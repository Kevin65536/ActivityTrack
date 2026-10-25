import argparse
import ctypes
import faulthandler
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import sys

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from src.break_reminder import BreakReminder
from src.config import Config
from src.runtime import NotificationBridge, ShutdownController, resolve_data_dir
from src.session_events import SessionEvents
from src.tracker import ActivityTrack
from src.ui.main_window import MainWindow
from src.ui.tray_icon import TrayIcon
from src.version import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(description='ActivityTrack: local input and screen-time statistics')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--data-dir', help='Explicit data directory (also isolates diagnostic runs)')
    parser.add_argument('--smoke-test', action='store_true', help='Exercise all tabs and orderly shutdown; requires --data-dir')
    parser.add_argument('--smoke-hooks', action='store_true', help='Also install real input hooks during the smoke test')
    parser.add_argument('--smoke-seconds', type=int, default=3)
    args = parser.parse_args(argv)
    if args.smoke_test and not args.data_dir:
        parser.error('--smoke-test requires an explicit isolated --data-dir')

    app = QApplication([sys.argv[0]])
    app.setApplicationName('ActivityTrack')
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)
    data_dir = resolve_data_dir(args.data_dir)
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        QMessageBox.critical(None, 'ActivityTrack', f'Cannot open data directory:\n{error}')
        return 1

    # Acquire ownership before opening the database or installing global hooks.
    instance_lock = QLockFile(str(data_dir / 'activitytrack.lock'))
    instance_lock.setStaleLockTime(0)
    if not instance_lock.tryLock(0):
        if not args.smoke_test:
            QMessageBox.information(None, 'ActivityTrack', 'ActivityTrack is already running for this data directory, or the directory is not writable.\n' + str(data_dir))
        return 2

    handler = RotatingFileHandler(data_dir / 'activitytrack.log', maxBytes=1_000_000, backupCount=3, encoding='utf-8')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s', handlers=[handler], force=True)
    logger = logging.getLogger('activitytrack')
    logger.info('Starting ActivityTrack %s', __version__)
    crash_stream = open(data_dir / 'crash.log', 'a', encoding='utf-8')
    faulthandler.enable(file=crash_stream, all_threads=True)
    window = None
    controller = None
    tracker = None
    smoke_errors = []

    def handle_exception(kind, error, tb):
        logger.error('Unhandled exception', exc_info=(kind, error, tb))
        if args.smoke_test:
            smoke_errors.append(str(error))
        else:
            QMessageBox.critical(window, 'ActivityTrack', str(error))
            if window:
                window.settings_tab.load_settings()

    previous_exception_hook = sys.excepthook
    sys.excepthook = handle_exception
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ActivityTrack')
        resource_dir = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
        icon = QIcon(str(resource_dir / 'resources' / 'icon.ico'))
        app.setWindowIcon(icon)
        config = Config(str(data_dir))
        if not args.smoke_test:
            config.sync_autostart_state()
        tracker = ActivityTrack(str(data_dir / 'tracker.db'))
        tracker.set_idle_timeout(config.idle_timeout_seconds)
        try:
            tracker.set_retention_days(config.data_retention_days)
        except Exception as error:
            tracker.write_error = str(error)
            logger.exception('Retention failed; the recorder will retry')
        skip_tracker = os.environ.get('SKIP_TRACKER') == '1'
        tracker.start(install_hooks=not skip_tracker and (not args.smoke_test or args.smoke_hooks))
        window = MainWindow(tracker, config)
        window.setWindowIcon(icon)
        tray = TrayIcon()
        reminder = BreakReminder(tracker, config)
        bridge = NotificationBridge(tray, config)
        reminder.set_notification_callback(bridge.requested.emit)
        if not args.smoke_test:
            reminder.start()
        session_events = SessionEvents(tracker)
        app.installNativeEventFilter(session_events)
        session_events.register(int(window.winId()))
        window.session_events = session_events
        controller = ShutdownController(app, tracker, reminder, window, tray, session_events)
        tray.show_window_signal.connect(window.showNormal)
        tray.show_window_signal.connect(window.activateWindow)
        tray.quit_signal.connect(controller.quit)
        window.quit_requested.connect(controller.quit)
        app.aboutToQuit.connect(lambda: controller.shutdown(show_error=False))

        def commit_session(manager):
            if not controller.shutdown(show_error=False):
                manager.cancel()

        app.commitDataRequest.connect(commit_session)
        signal.signal(signal.SIGINT, lambda *_: controller.quit())
        signal.signal(signal.SIGTERM, lambda *_: controller.quit())
        timer = QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(500)
        session_retry = QTimer()
        session_retry.timeout.connect(lambda: session_events.register(int(window.winId())))
        session_retry.start(30_000)
        window.show()

        if config.load_error and not args.smoke_test:
            QTimer.singleShot(0, lambda: QMessageBox.warning(window, 'ActivityTrack', config.load_error))

        if args.smoke_test:
            # Verify real Qt widgets, optional hooks, a transaction, exports and
            # the same shutdown path used by the tray.
            def finish_smoke():
                from src.exporter import DataExporter
                result = {'version': __version__, 'tabs': window.tabs.count()}
                try:
                    for index in range(window.tabs.count()):
                        window.tabs.setCurrentIndex(index)
                        window.update_stats()
                        app.processEvents()
                    tracker.flush_stats()
                    health = tracker.get_health_snapshot()
                    result['health'] = health
                    result['session_notifications'] = session_events.error is None
                    if args.smoke_hooks and not health['hooks_active']:
                        raise RuntimeError(health['hook_error'] or 'Native input hooks did not start')
                    if health['write_error'] or health['processing_error']:
                        raise RuntimeError('Recorder reported an error')
                    exporter = DataExporter(tracker.db)
                    if not exporter.export_json(str(data_dir / 'smoke-export.json')):
                        raise RuntimeError(exporter.last_error)
                    with tracker.db.read_connection() as conn:
                        result['database_check'] = conn.execute('PRAGMA integrity_check').fetchone()[0]
                    if result['database_check'] != 'ok':
                        raise RuntimeError('Database integrity check failed')
                except Exception as error:
                    logger.exception('Smoke test failed')
                    smoke_errors.append(str(error))
                stopped = controller.shutdown(show_error=False)
                result.update(ok=not smoke_errors and stopped, errors=smoke_errors, shutdown=stopped)
                (data_dir / 'smoke-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
                app.exit(0 if result['ok'] else 1)

            QTimer.singleShot(max(1, args.smoke_seconds) * 1000, finish_smoke)

        return app.exec()
    except Exception as error:
        handle_exception(type(error), error, error.__traceback__)
        return 1
    finally:
        if controller:
            controller.shutdown(show_error=False)
        elif tracker:
            try:
                tracker.stop()
            except Exception:
                logger.exception('Startup cleanup could not save activity')
        faulthandler.disable()
        crash_stream.close()
        instance_lock.unlock()
        sys.excepthook = previous_exception_hook
        logging.shutdown()


if __name__ == '__main__':
    sys.exit(main())
