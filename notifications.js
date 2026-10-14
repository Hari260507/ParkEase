/* ParkEase Step 4: Browser Notifications
   Include this script on pages where booking success or expiry reminders should work.
   Browser notifications require permission and generally work on localhost/HTTPS.
*/
(function () {
  "use strict";

  const STORAGE_KEY = "parkease_notification_reminders";

  function notify(title, body) {
    if (!("Notification" in window)) {
      console.warn("This browser does not support notifications.");
      return;
    }
    if (Notification.permission === "granted") {
      new Notification(title, { body: body, icon: "favicon.ico" });
    } else if (Notification.permission === "default") {
      Notification.requestPermission().then(function (permission) {
        if (permission === "granted") {
          new Notification(title, { body: body, icon: "favicon.ico" });
        }
      });
    }
  }

  function readReminders() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    } catch (_) {
      return [];
    }
  }

  function saveReminders(items) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }

  // Call after a booking is successfully confirmed.
  window.ParkEaseNotifications = {
    bookingSuccess: function (slotName) {
      notify("ParkEase: Booking Confirmed", "Your parking slot " +
        (slotName || "") + " has been booked successfully.");
    },

    // Call with the booking's end date/time in a format Date can parse.
    scheduleExpiryReminder: function (bookingId, slotName, endDateTime) {
      const endMs = new Date(endDateTime).getTime();
      if (!bookingId || !Number.isFinite(endMs)) {
        console.warn("Reminder not scheduled: booking ID or end time is invalid.");
        return;
      }
      const reminders = readReminders().filter(function (item) {
        return item.bookingId !== String(bookingId);
      });
      reminders.push({
        bookingId: String(bookingId),
        slotName: String(slotName || ""),
        remindAt: endMs - 5 * 60 * 1000,
        endAt: endMs,
        sent: false
      });
      saveReminders(reminders);
    }
  };

  // Checks reminders while this page remains open. Browser timers cannot reliably
  // notify if the browser is fully closed or the computer is asleep.
  function checkReminders() {
    const now = Date.now();
    const reminders = readReminders();
    let changed = false;
    reminders.forEach(function (item) {
      if (!item.sent && now >= item.remindAt && now < item.endAt) {
        notify("ParkEase: Parking Ending Soon",
          "Slot " + item.slotName + " booking ends in about 5 minutes.");
        item.sent = true;
        changed = true;
      }
    });
    if (changed) saveReminders(reminders);
  }

  if ("Notification" in window && Notification.permission === "default") {
    // Ask permission only after an explicit user action via the button below.
  }

  window.ParkEaseNotifications.enable = function () {
    if (!("Notification" in window)) {
      alert("Notifications are not supported by this browser.");
      return Promise.resolve(false);
    }
    return Notification.requestPermission().then(function (permission) {
      if (permission === "granted") {
        notify("ParkEase Notifications Enabled", "You can receive booking reminders while this page is open.");
        return true;
      }
      alert("Notification permission was not granted. You can enable it in browser settings.");
      return false;
    });
  };

  checkReminders();
  window.setInterval(checkReminders, 30 * 1000);
})();
