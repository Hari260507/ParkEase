```javascript
function showMessage() {
    alert("Welcome to Parking Slot Management System!");
}

// Check parking booking reminders
function checkBookingReminders() {
    const now = Date.now();

    for (let i = 1; i <= 100; i++) {
        const slot = "A" + i;
        const key = "booking_" + slot;
        const saved = localStorage.getItem(key);

        if (!saved) continue;

        try {
            const booking = JSON.parse(saved);

            const reminderTime = new Date(
                booking.reminderTime
            ).getTime();

            const endTime = new Date(
                booking.endTime
            ).getTime();

            const startTime = new Date(
                booking.startTime
            ).getTime();

            // Ignore invalid booking times
            if (
                !Number.isFinite(reminderTime) ||
                !Number.isFinite(endTime) ||
                !Number.isFinite(startTime)
            ) {
                continue;
            }

            // Show reminder only during the final 5 minutes
            if (
                now >= reminderTime &&
                now < endTime &&
                now >= startTime &&
                !booking.reminderShown
            ) {
                booking.reminderShown = true;

                // Save first to prevent duplicate reminders
                localStorage.setItem(
                    key,
                    JSON.stringify(booking)
                );

                alert(
                    "Parking Reminder!\n\n" +
                    "Your booking for slot " + slot +
                    " will end in approximately 5 minutes.\n\n" +
                    "Please prepare to leave the parking slot."
                );
            }
        } catch (error) {
            console.error(
                "Unable to check reminder for " + slot,
                error
            );
        }
    }
}

// Check immediately and every 10 seconds
checkBookingReminders();
setInterval(checkBookingReminders, 10000);
```
