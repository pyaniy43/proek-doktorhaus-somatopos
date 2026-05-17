// script.js - Соматопос с интеграцией нейросети

let currentUser = localStorage.getItem('somatopos_user') || null;
let usersDB = [];
let historyDB = [];
let autoRefreshInterval = null;

// Загрузка базы данных
const loadDB = async () => {
    try {
        const res = await fetch('/api/db');
        const data = await res.json();
        usersDB = data.users || [];
        historyDB = data.history || [];
        renderUsers();
        renderHistory();
        updateAuthUI();
    } catch (e) {
        console.error("Failed to load DB:", e);
    }
};

// Получение последнего диагноза от нейросети
const fetchLastDiagnosis = async () => {
    try {
        const response = await fetch('/last_diagnosis.json?_=' + Date.now()); // Добавляем timestamp чтобы избежать кэша
        if (!response.ok) {
            return null;
        }
        return await response.json();
    } catch (e) {
        console.error("Ошибка загрузки диагноза:", e);
        return null;
    }
};

// Обновление UI по данным из JSON
const updateUIFromDiagnosis = async () => {
    const data = await fetchLastDiagnosis();

    if (data && data.last_diagnosis) {
        const diag = data.last_diagnosis;

        // Обновляем показатели
        const hrEl = document.getElementById('val-hr');
        const muscleEl = document.getElementById('val-muscle');
        const brainEl = document.getElementById('val-brain');

        if (hrEl) hrEl.innerHTML = `${diag.bpm} <span class="metric-unit">уд/мин</span>`;
        if (muscleEl) muscleEl.innerHTML = `${diag.muscle} <span class="metric-unit">%</span>`;
        if (brainEl) brainEl.innerHTML = `${diag.eeg} <span class="metric-unit">%</span>`;

        // Обновляем диагноз в AI блоке
        const aiTitle = document.querySelector('.ai-status');
        const aiDesc = document.querySelector('.ai-desc');

        if (aiTitle) {
            aiTitle.textContent = diag.diagnosis_short;
            aiTitle.style.color = getColorByCode(diag.diagnosis_code);
        }
        if (aiDesc) {
            aiDesc.innerHTML = `${diag.diagnosis_full}<br><br><strong>Уверенность модели:</strong> ${diag.confidence.toFixed(1)}%`;
        }

        // Обновляем SVG зоны
        updateSVGFromDiagnosis(diag);
    } else {
        // Нет данных
        const aiStatus = document.querySelector('.ai-status');
        if (aiStatus) {
            aiStatus.textContent = "Ожидание данных...";
            aiStatus.style.color = "#94a3b8";
        }
    }
};

// Цвет диагноза
const getColorByCode = (code) => {
    switch(code) {
        case 'heart': return '#fbbf24';
        case 'muscle_head': return '#fbbf24';
        case 'brain': return '#fbbf24';
        case 'combined': return '#fb7185';
        default: return '#34d399';
    }
};

// Обновление SVG на основе диагноза
const updateSVGFromDiagnosis = (diag) => {
    // Сброс всех зон
    document.querySelectorAll('.body-zone').forEach(zone => {
        zone.classList.remove('zone-warning', 'zone-critical');
        zone.setAttribute('data-state', '0');
    });

    // Подсветка зон в зависимости от диагноза
    if (diag.diagnosis_code === 'heart') {
        const heartZone = document.getElementById('heart_zone');
        if (heartZone) {
            heartZone.classList.add('zone-warning');
            heartZone.setAttribute('data-state', '1');
        }
    } else if (diag.diagnosis_code === 'muscle_head') {
        const torso = document.getElementById('torso_zone');
        const arms = [document.getElementById('left_arm'), document.getElementById('right_arm')];
        if (torso) {
            torso.classList.add('zone-warning');
            torso.setAttribute('data-state', '1');
        }
        arms.forEach(arm => {
            if (arm) {
                arm.classList.add('zone-warning');
                arm.setAttribute('data-state', '1');
            }
        });
    } else if (diag.diagnosis_code === 'brain') {
        const head = document.getElementById('head_zone');
        if (head) {
            head.classList.add('zone-warning');
            head.setAttribute('data-state', '1');
        }
    } else if (diag.diagnosis_code === 'combined') {
        const heart = document.getElementById('heart_zone');
        const head = document.getElementById('head_zone');
        if (heart) heart.classList.add('zone-critical');
        if (head) head.classList.add('zone-warning');
    }
};

// Автообновление
const startAutoRefresh = () => {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(() => {
        updateUIFromDiagnosis();
    }, 2000); // Обновляем каждые 2 секунды
};

// Auth UI
const updateAuthUI = () => {
    const loginBox = document.getElementById('auth-login');
    const profileBox = document.getElementById('auth-profile');
    const nameLabel = document.getElementById('current-username');
    const adminBadge = document.getElementById('admin-badge');

    if (currentUser) {
        if (loginBox) loginBox.style.display = 'none';
        if (profileBox) profileBox.style.display = 'flex';
        if (nameLabel) nameLabel.textContent = currentUser;
    } else {
        if (loginBox) loginBox.style.display = 'flex';
        if (profileBox) profileBox.style.display = 'none';
    }
};

// Рендер пользователей
const renderUsers = () => {
    const list = document.getElementById('users-list');
    const datalist = document.getElementById('user-suggestions');

    if (datalist) {
        datalist.innerHTML = usersDB.map(u => `<option value="${u.name}"></option>`).join('');
    }
    if (!list) return;

    const filteredUsers = usersDB.filter(u => u.name !== 'admin');
    if (filteredUsers.length === 0) {
        list.innerHTML = '<div class="empty-msg">Пациенты не найдены.</div>';
        return;
    }
    list.innerHTML = filteredUsers.map(u => `
        <div class="data-item user-item ${selectedHistoryUser === u.name ? 'active' : ''}" onclick="selectUserHistory('${u.name}')">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            ${u.name}
        </div>
    `).join('');
};

let selectedHistoryUser = currentUser;

window.selectUserHistory = (name) => {
    selectedHistoryUser = name;
    renderUsers();
    renderHistory();
};

const renderHistory = () => {
    const list = document.getElementById('history-list');
    if (!list) return;

    const userHistory = historyDB.filter(h => h.user === selectedHistoryUser);
    if (userHistory.length === 0) {
        list.innerHTML = '<div class="empty-msg">История пуста.</div>';
        return;
    }

    list.innerHTML = userHistory.map(h => `
        <div class="data-item">
            <div class="hist-date">${h.date} - <strong>${h.state || 'Анализ'}</strong></div>
            <div class="hist-metrics">
                ЧСС: ${h.metrics?.hr || '-'} | ЭМГ: ${h.metrics?.muscle || '-'}% | ЭЭГ: ${h.metrics?.brain || '-'}%
            </div>
        </div>
    `).join('');
};

// Tooltips
document.querySelectorAll('.body-zone').forEach(zone => {
    const tooltip = document.getElementById('tooltip');
    const ttTitle = document.getElementById('tt-title');
    const ttStatus = document.getElementById('tt-status');

    zone.addEventListener('mouseenter', () => {
        ttTitle.textContent = zone.dataset.name;
        const state = parseInt(zone.dataset.state || '0');
        if (state === 2) {
            ttStatus.innerHTML = '<span class="val-critical">Критическая зона</span>';
        } else if (state === 1) {
            ttStatus.innerHTML = '<span class="val-warning">Обнаружен стресс/спазм</span>';
        } else {
            ttStatus.innerHTML = '<span class="val-normal">Функционирует нормально</span>';
        }
        tooltip.classList.add('visible');
    });
    zone.addEventListener('mouseleave', () => {
        tooltip.classList.remove('visible');
    });
});

// Login/Logout
document.getElementById('btn-login')?.addEventListener('click', async () => {
    const name = document.getElementById('username-input')?.value.trim();
    const pass = document.getElementById('password-input')?.value.trim();

    if (!name || !pass) {
        alert('Введите имя и пароль');
        return;
    }

    const existingUser = usersDB.find(u => u.name === name);
    if (existingUser && existingUser.password !== pass) {
        alert('Неверный пароль');
        return;
    }

    currentUser = name;
    selectedHistoryUser = name;
    localStorage.setItem('somatopos_user', currentUser);
    updateAuthUI();
    renderUsers();
    renderHistory();
});

document.getElementById('btn-logout')?.addEventListener('click', () => {
    currentUser = null;
    localStorage.removeItem('somatopos_user');
    updateAuthUI();
    renderUsers();
    renderHistory();
});

// Инициализация
updateUIFromDiagnosis();
startAutoRefresh();
loadDB();