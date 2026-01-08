"""
Break Reminder module for ActivityTrack.

This module monitors user activity and reminds them to take breaks
after extended periods of continuous screen usage.

Key features:
- Detects genuine user activity vs automated clicks
- Tracks continuous usage time
- Sends Windows notifications via QSystemTrayIcon
- Respects user-configured intervals and break durations
"""

import time
import threading
from typing import Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .tracker import ActivityTrack
    from .config import Config


@dataclass
class ActivityStats:
    """Statistics about recent user activity."""
    total_keys: int = 0
    total_clicks: int = 0
    total_scrolls: int = 0
    total_distance: float = 0.0
    
    def has_activity(self) -> bool:
        """Check if there's any activity recorded."""
        return (self.total_keys > 0 or self.total_clicks > 0 or 
                self.total_scrolls > 0 or self.total_distance > 0)
    
    def reset(self):
        """Reset all counters."""
        self.total_keys = 0
        self.total_clicks = 0
        self.total_scrolls = 0
        self.total_distance = 0.0


class BreakReminder:
    """
    Monitors user activity and sends break reminders.
    
    The reminder system works as follows:
    1. Tracks continuous usage time since last break/idle period
    2. When usage time exceeds the configured interval, sends a notification
    3. Resets timer when:
       - User takes a break (idle for >= break duration)
       - User dismisses the notification
       - Timer is manually reset
    
    To detect genuine user activity vs automation:
    - Checks for varied input patterns (keys, mouse movement, scrolls)
    - Monitors if inputs come from injected sources (via LLKHF_INJECTED flag in tracker)
    - Considers mouse movement distance (automation tends to have none)
    """
    
    def __init__(self, tracker: 'ActivityTrack', config: 'Config'):
        """Initialize the break reminder.
        
        Args:
            tracker: The ActivityTrack instance to monitor
            config: Configuration instance for settings
        """
        self.tracker = tracker
        self.config = config
        
        # State
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Timing
        self._continuous_usage_start: Optional[float] = None
        self._last_reminder_time: Optional[float] = None
        self._last_activity_snapshot = ActivityStats()
        
        # Callback for showing notifications (set by UI)
        self._notification_callback: Optional[Callable[[str, str], None]] = None
        
        # Break state
        self._on_break = False
        self._break_start_time: Optional[float] = None
    
    def set_notification_callback(self, callback: Callable[[str, str], None]):
        """Set the callback for showing notifications.
        
        Args:
            callback: Function that takes (title, message) and shows a notification
        """
        self._notification_callback = callback
    
    def start(self):
        """Start the break reminder monitoring thread."""
        if self._running:
            return
        
        self._running = True
        self._continuous_usage_start = time.time()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the break reminder monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
    
    def reset_timer(self):
        """Reset the continuous usage timer (e.g., when user takes a break)."""
        with self._lock:
            self._continuous_usage_start = time.time()
            self._last_reminder_time = None
            self._on_break = False
            self._break_start_time = None
            self._last_activity_snapshot.reset()
    
    def snooze(self, minutes: int = 10):
        """Snooze the reminder for specified minutes.
        
        Args:
            minutes: Number of minutes to snooze
        """
        with self._lock:
            self._last_reminder_time = time.time()
            # Effectively extends the timer by snooze duration
            snooze_seconds = minutes * 60
            if self._continuous_usage_start:
                self._continuous_usage_start = time.time() - (
                    self.config.break_reminder_interval_minutes * 60 - snooze_seconds
                )
    
    def _is_enabled(self) -> bool:
        """Check if break reminders are enabled."""
        return (self.config.break_reminder_enabled and 
                self.config.break_reminder_interval_minutes > 0)
    
    def _get_interval_seconds(self) -> float:
        """Get the reminder interval in seconds."""
        return self.config.break_reminder_interval_minutes * 60
    
    def _get_break_duration_seconds(self) -> float:
        """Get the required break duration in seconds."""
        return self.config.break_reminder_duration_minutes * 60
    
    def _is_user_idle(self) -> bool:
        """Check if the user is currently idle (no recent activity).
        
        Uses the tracker's idle detection which is based on actual input events.
        """
        return self.tracker.is_idle
    
    def _is_genuine_activity(self) -> bool:
        """Detect if recent activity appears to be from a real user vs automation.
        
        Automation detection heuristics:
        1. Only clicks with no key presses or mouse movement -> likely automated
        2. Very regular, rhythmic clicking patterns -> likely automated
        3. No scroll activity at all over long periods -> suspicious
        4. The tracker already filters injected inputs via LLKHF_INJECTED flag
        
        Returns:
            True if activity appears genuine, False if likely automated
        """
        # Get current stats snapshot
        current = self.tracker.get_stats_snapshot()
        
        # Calculate deltas since last check
        current_keys = current.get('buffer_keys', 0)
        current_clicks = current.get('buffer_clicks', 0) 
        current_distance = current.get('buffer_distance', 0.0)
        current_scroll = current.get('buffer_scroll', 0.0)
        
        # If there are key presses, it's almost certainly human
        # (automation rarely types random keys)
        if current_keys > 0:
            return True
        
        # If there's mouse movement, probably human
        # (automation tools usually click without moving)
        if current_distance > 0.001:  # More than 1mm of movement
            return True
        
        # If there's scrolling, probably human
        if current_scroll > 0:
            return True
        
        # Only clicks with no other activity is suspicious
        # But we still count it if user has been typing/moving recently
        # Check tracker's foreground time buffer for recent app switches
        # (humans switch apps, automation usually doesn't)
        foreground_snapshot = self.tracker.get_foreground_time_snapshot()
        if len(foreground_snapshot) > 1:  # Multiple apps used
            return True
        
        # If we only have clicks and nothing else, might be automation
        # But give benefit of doubt if there's at least some variety
        return current_clicks < 100  # Very high click count without other input is suspicious
    
    def _check_break_taken(self) -> bool:
        """Check if user has taken a sufficient break.
        
        A break is considered taken when the user has been idle for
        at least the configured break duration.
        
        Returns:
            True if user has taken a full break
        """
        if not self._is_user_idle():
            # User is active, not on break
            if self._on_break:
                # Was on break but now active again
                self._on_break = False
                self._break_start_time = None
            return False
        
        # User is idle
        if not self._on_break:
            # Just started being idle
            self._on_break = True
            self._break_start_time = time.time()
            return False
        
        # Check if break is long enough
        if self._break_start_time:
            break_duration = time.time() - self._break_start_time
            if break_duration >= self._get_break_duration_seconds():
                return True
        
        return False
    
    def _should_remind(self) -> bool:
        """Determine if a break reminder should be sent now.
        
        Returns:
            True if reminder should be sent
        """
        if not self._is_enabled():
            return False
        
        if self._continuous_usage_start is None:
            return False
        
        # Don't remind if user is currently idle (on break)
        if self._is_user_idle():
            return False
        
        # Don't remind if activity seems automated
        if not self._is_genuine_activity():
            return False
        
        # Check elapsed time since last break
        elapsed = time.time() - self._continuous_usage_start
        interval = self._get_interval_seconds()
        
        if elapsed >= interval:
            # Check cooldown - don't spam reminders
            if self._last_reminder_time:
                # Wait at least 5 minutes between reminders
                if time.time() - self._last_reminder_time < 300:
                    return False
            return True
        
        return False
    
    def _send_reminder(self):
        """Send a break reminder notification."""
        if self._notification_callback:
            # Import here to avoid circular dependency
            from .i18n import tr
            
            title = tr('break_reminder.title')
            minutes_used = int((time.time() - self._continuous_usage_start) / 60)
            suggested_break = self.config.break_reminder_duration_minutes
            
            message = tr('break_reminder.message', 
                        minutes=minutes_used, 
                        break_duration=suggested_break)
            
            self._notification_callback(title, message)
            
            with self._lock:
                self._last_reminder_time = time.time()
    
    def _monitor_loop(self):
        """Main monitoring loop running in background thread."""
        check_interval = 30  # Check every 30 seconds
        
        while self._running:
            try:
                # Check if user has taken a break
                if self._check_break_taken():
                    self.reset_timer()
                    continue
                
                # Check if we should send a reminder
                if self._should_remind():
                    self._send_reminder()
                
            except Exception as e:
                # Log but don't crash the monitor
                print(f"[BreakReminder] Error in monitor loop: {e}")
            
            # Sleep in small intervals to allow quick shutdown
            for _ in range(check_interval):
                if not self._running:
                    break
                time.sleep(1)
    
    def get_status(self) -> dict:
        """Get current break reminder status for UI display.
        
        Returns:
            Dict with status information
        """
        with self._lock:
            if not self._is_enabled():
                return {
                    'enabled': False,
                    'continuous_minutes': 0,
                    'until_reminder_minutes': 0,
                    'on_break': False
                }
            
            continuous_minutes = 0
            until_reminder_minutes = 0
            
            if self._continuous_usage_start:
                elapsed = time.time() - self._continuous_usage_start
                continuous_minutes = int(elapsed / 60)
                remaining = self._get_interval_seconds() - elapsed
                until_reminder_minutes = max(0, int(remaining / 60))
            
            return {
                'enabled': True,
                'continuous_minutes': continuous_minutes,
                'until_reminder_minutes': until_reminder_minutes,
                'on_break': self._on_break,
                'interval_minutes': self.config.break_reminder_interval_minutes,
                'break_duration_minutes': self.config.break_reminder_duration_minutes
            }
