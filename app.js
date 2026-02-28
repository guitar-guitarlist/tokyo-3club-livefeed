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

function renderSchedule(data) {
    const grid = document.getElementById('schedule-container');
    const nav = document.getElementById('month-nav');
    const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    let currentMonthKey = '';

    data.forEach(dayInfo => {
        const d = dayInfo.date;
        const year = d.getFullYear();
        const monthIndex = d.getMonth();
        const monthKey = `${year}-${monthIndex}`;

        // Month Divider and Nav Button
        if (monthKey !== currentMonthKey) {
            currentMonthKey = monthKey;

            const monthLabel = `${year}年 ${monthIndex + 1}月`;
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
            navBtn.innerText = `${monthIndex + 1}月`;
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

        // Date Column
        const dateCol = document.createElement('div');
        dateCol.className = 'date-column';
        dateCol.innerHTML = `
            <span class="date-month">${months[monthIndex]}</span>
            <span class="date-day">${String(d.getDate()).padStart(2, '0')}</span>
            <span class="date-weekday ${wkClass}">${weekdays[wk]}</span>
        `;
        grid.appendChild(dateCol);

        // Venues
        grid.appendChild(createEventCard('bn', dayInfo.bluenote));
        grid.appendChild(createEventCard('bb', dayInfo.billboard));
        grid.appendChild(createEventCard('cc', dayInfo.cotton));
    });
}

function createEventCard(venueCode, eventInfo) {
    const wrapper = document.createElement('div');
    const venueMap = { bn: 'Blue Note Tokyo', bb: 'Billboard Live', cc: 'Cotton Club' };
    const venueName = venueMap[venueCode];

    if (!eventInfo) {
        wrapper.className = `empty-slot card-${venueCode}`;
        wrapper.innerHTML = `
            <div class="mobile-venue-label">${venueName}</div>
            <div class="empty-text">No Schedule</div>
        `;
        return wrapper;
    }

    wrapper.className = `event-card card-${venueCode}`;

    if (eventInfo.url) {
        wrapper.addEventListener('click', () => {
            window.open(eventInfo.url, '_blank', 'noopener,noreferrer');
        });
        wrapper.style.cursor = 'pointer'; // Ensure it looks clickable
    } else {
        wrapper.style.cursor = 'default';
    }

    wrapper.innerHTML = `
        <div class="event-content">
            <div class="mobile-venue-label">${venueName}</div>
            <div class="event-artist">${eventInfo.artist}</div>
            <div class="event-time">${eventInfo.time}</div>
        </div>
    `;

    return wrapper;
}
