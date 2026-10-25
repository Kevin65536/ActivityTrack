from functools import wraps


def coherent_refresh(method):
    """Read the database and buffers together; skip a frame during a slow write."""
    @wraps(method)
    def refresh(self, *args, **kwargs):
        tracker = self.tracker
        if not tracker:
            return method(self, *args, **kwargs)
        if not tracker.lock.acquire(blocking=False):
            return
        try:
            return method(self, *args, **kwargs)
        finally:
            tracker.lock.release()
    return refresh


def health_message(health, chinese=False):
    if health.get('write_error'):
        text = '保存失败，数据仍在内存中；请勿强制退出' if chinese else 'Save failed; data is buffered. Keep the app open.'
    elif health.get('hook_error') or health.get('processing_error'):
        text = '记录异常，请检查诊断日志并重启' if chinese else 'Recording error; check diagnostics and restart.'
    elif health.get('worker_delayed'):
        text = '记录处理延迟' if chinese else 'Recording is delayed'
    elif health.get('dropped_events'):
        text = f"队列过载，已丢失 {health['dropped_events']} 个输入事件" if chinese else f"Queue overloaded; {health['dropped_events']} input events lost"
    elif not health.get('running'):
        text = '记录已停止' if chinese else 'Recording stopped'
    elif health.get('hooks_requested') and not health.get('hooks_active'):
        text = '输入钩子未运行' if chinese else 'Input hooks are not running'
    elif health.get('paused'):
        return ('记录已暂停（锁屏或休眠）' if chinese else 'Recording paused (lock or suspend)'), False
    else:
        return ('正在记录' if chinese else 'Recording'), False
    return text, True
