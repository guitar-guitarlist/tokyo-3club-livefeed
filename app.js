document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('schedule.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const scheduleData = await response.json();

        // Convert date strings back to Date objects
        const parsedData = scheduleData.map(item => ({
            ...item,
            date: new Date(item.date)
        }));

        renderSchedule(parsedData);
    } catch (error) {
        console.error("Failed to load schedule data:", error);
        document.getElementById('schedule-container').innerHTML = `
            <div class="error-message" style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: #ef4444;">
                <p>Failed to load schedule data.</p>
                <p style="font-size: 0.9rem; margin-top: 1rem; color: #94a3b8;">Please run the backend fetcher script first.</p>
            </div>
        `;
    }
});

const todayDate = new Date();
todayDate.setHours(0, 0, 0, 0);

function isNewEvent(firstSeenStr) {
    if (!firstSeenStr) return false;
    const fsDate = new Date(firstSeenStr);
    fsDate.setHours(0, 0, 0, 0);
    const diffTime = todayDate.getTime() - fsDate.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    return diffDays >= 0 && diffDays <= 3;
}

function renderSchedule(data) {
    const grid = document.getElementById('schedule-container');
    const nav = document.getElementById('month-nav');
    nav.innerHTML = ''; // Start empty for re-rendering

    // Create Today Button
    const todayBtn = document.createElement('button');
    todayBtn.className = 'month-nav-btn today-btn';
    todayBtn.innerText = 'Today';
    todayBtn.addEventListener('click', () => {
        const todayTarget = document.getElementById('today-item');
        if (todayTarget) {
            const yOffset = -140; // offset for sticky nav and headers
            const y = todayTarget.getBoundingClientRect().top + window.pageYOffset + yOffset;
            window.scrollTo({ top: y, behavior: 'smooth' });
        }
    });
    nav.appendChild(todayBtn);

    const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    let currentMonthKey = '';
    const newEvents = [];

    data.forEach(dayInfo => {
        const d = dayInfo.date;
        const year = d.getFullYear();
        const monthIndex = d.getMonth();
        const monthKey = `${year}-${monthIndex}`;

        // Collect new events
        ['bn', 'bb', 'cc'].forEach(venueCode => {
            const venueKey = venueCode === 'bn' ? 'bluenote' : venueCode === 'bb' ? 'billboard' : 'cotton';
            const eventInfo = dayInfo[venueKey];
            if (eventInfo && eventInfo.artist && isNewEvent(eventInfo.first_seen)) {
                newEvents.push({ date: d, venueCode, eventInfo });
            }
        });

        // Month Divider and Nav Button
        if (monthKey !== currentMonthKey) {
            currentMonthKey = monthKey;

            const monthLabel = `${months[monthIndex]} ${year}`;
            const headerId = `month-${monthKey}`;

            // Add Divider to Grid
            const divider = document.createElement('div');
            divider.className = 'month-divider';
            divider.id = headerId;
            divider.innerHTML = `<h2>${monthLabel}</h2>`;
            grid.appendChild(divider);

            // Add Button to Nav
            const navBtn = document.createElement('button');
            navBtn.className = 'month-nav-btn';
            navBtn.innerText = months[monthIndex];
            navBtn.addEventListener('click', () => {
                const target = document.getElementById(headerId);
                if (target) {
                    const yOffset = -80; // offset for sticky nav
                    const y = target.getBoundingClientRect().top + window.pageYOffset + yOffset;
                    window.scrollTo({ top: y, behavior: 'smooth' });
                }
            });
            nav.appendChild(navBtn);
        }

        const wk = d.getDay();
        const wkClass = wk === 0 ? 'weekday-sun' : wk === 6 ? 'weekday-sat' : '';
        const isToday = d.getFullYear() === todayDate.getFullYear() && d.getMonth() === todayDate.getMonth() && d.getDate() === todayDate.getDate();

        // Date Column
        const dateCol = document.createElement('div');
        dateCol.className = `date-column ${isToday ? 'date-today' : ''}`;
        if (isToday) dateCol.id = 'today-item';
        dateCol.innerHTML = `
            <span class="date-month">${months[monthIndex]}</span>
            <span class="date-day">${String(d.getDate()).padStart(2, '0')}</span>
            <span class="date-weekday ${wkClass}">${weekdays[wk]}</span>
        `;
        grid.appendChild(dateCol);

        // Venues
        grid.appendChild(createEventCard('bn', dayInfo.bluenote, d, isToday));
        grid.appendChild(createEventCard('bb', dayInfo.billboard, d, isToday));
        grid.appendChild(createEventCard('cc', dayInfo.cotton, d, isToday));
    });

    renderRecentlyAdded(newEvents, months, weekdays);

    // Initial scroll to today
    setTimeout(() => {
        const todayTarget = document.getElementById('today-item');
        if (todayTarget) {
            const yOffset = -140;
            const y = todayTarget.getBoundingClientRect().top + window.pageYOffset + yOffset;
            window.scrollTo({ top: y, behavior: 'smooth' });
        }
    }, 100);
}

function createEventCard(venueCode, eventInfo, dateObj = null, isToday = false) {
    const wrapper = document.createElement('div');
    const venueMap = { bn: 'Blue Note Tokyo', bb: 'Billboard Live', cc: 'Cotton Club' };
    const venueName = venueMap[venueCode];

    let baseClass = isToday ? 'is-today ' : '';

    if (!eventInfo) {
        wrapper.className = `${baseClass}empty-slot card-${venueCode}`;
        wrapper.innerHTML = `
            <div class="mobile-venue-label">${venueName}</div>
            <div class="empty-text">No Schedule</div>
        `;
        return wrapper;
    }

    wrapper.className = `${baseClass}event-card card-${venueCode}`;

    if (eventInfo.url) {
        wrapper.addEventListener('click', () => {
            window.open(eventInfo.url, '_blank', 'noopener,noreferrer');
        });
        wrapper.style.cursor = 'pointer'; // Ensure it looks clickable
    } else {
        wrapper.style.cursor = 'default';
    }

    const isNew = isNewEvent(eventInfo.first_seen);
    const newBadgeHtml = isNew ? `<span class="new-badge">NEW</span>` : '';

    let dateDisplayHtml = '';
    if (dateObj) {
        const dStr = `${dateObj.getMonth() + 1}/${dateObj.getDate()}`;
        dateDisplayHtml = `<div class="event-date-mini">${dStr}</div>`;
    }

    wrapper.innerHTML = `
        <div class="event-content">
            <div class="mobile-venue-label">${venueName}</div>
            ${dateDisplayHtml}
            ${newBadgeHtml}
            <div class="event-artist">${eventInfo.artist}</div>
            <div class="event-time">${eventInfo.time}</div>
        </div>
    `;

    return wrapper;
}

function renderRecentlyAdded(newEvents, months, weekdays) {
    const section = document.getElementById('recently-added-section');
    const container = document.getElementById('recently-added-container');

    if (newEvents.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    container.innerHTML = ''; // Clear

    // Sort new events by date (earliest first or keep order)
    newEvents.forEach(item => {
        const card = createEventCard(item.venueCode, item.eventInfo, item.date);
        container.appendChild(card);
    });
}
