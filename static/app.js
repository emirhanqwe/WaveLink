const socket = io();
let currentDuration = 0;
let currentPosition = 0;
let isPlaying = false;
let progressInterval = null;
let currentSongId = "";
let isUserSeeking = false;

socket.on('connect', () => console.log('Bağlandı'));
socket.on('disconnect', () => console.log('Koptu'));

socket.on('update_media', function(data) {
    document.getElementById('title').innerText = data.title;
    document.getElementById('artist').innerText = data.artist;
    
    const artDiv = document.getElementById('art');
    if (data.cover_url) {
        artDiv.style.backgroundImage = `url('${data.cover_url}')`;
        artDiv.innerHTML = '';
    } else {
        artDiv.style.backgroundImage = 'none';
        artDiv.innerHTML = `
            <div class="placeholder">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
                </svg>
            </div>
        `;
    }

    if (data.color) {
        document.documentElement.style.setProperty('--dynamic-color', data.color);
    } else {
        document.documentElement.style.setProperty('--dynamic-color', '#6366f1');
    }
    
    currentDuration = data.duration_ms || 0;
    isPlaying = data.is_playing;

    const newSongId = `${data.title}-${data.artist}`;

    if (newSongId !== currentSongId) {
        currentSongId = newSongId;
        currentPosition = data.position_ms || 0;
    } else if (!isUserSeeking) {
        const serverPosition = data.position_ms || 0;
        const diff = Math.abs(serverPosition - currentPosition);
        
        if (!isPlaying || diff > 3500) {
            currentPosition = serverPosition;
        }
    }
    
    updateProgressBar();
    
    const iconPlay = document.getElementById('icon-play');
    const iconPause = document.getElementById('icon-pause');
    
    if (isPlaying) {
        iconPlay.style.display = 'none';
        iconPause.style.display = 'block';
        startProgressTimer();
    } else {
        iconPlay.style.display = 'block';
        iconPause.style.display = 'none';
        stopProgressTimer();
    }
});

function updateProgressBar() {
    const percent = currentDuration > 0 ? (currentPosition / currentDuration) * 100 : 0;
    document.getElementById('progress-fill').style.width = Math.min(100, Math.max(0, percent)) + '%';
    
    document.getElementById('current-time').innerText = formatTime(currentPosition);
    document.getElementById('total-time').innerText = formatTime(currentDuration);
}

function startProgressTimer() {
    if (progressInterval !== null) return;

    progressInterval = setInterval(() => {
        if (isPlaying && currentPosition < currentDuration) {
            currentPosition += 250;
            updateProgressBar();
        }
    }, 250);
}

function stopProgressTimer() {
    if (progressInterval !== null) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

function formatTime(ms) {
    if (!ms || ms === 0) return '0:00';
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function seekTo(event) {
    isUserSeeking = true;
    const bar = event.currentTarget;
    const rect = bar.getBoundingClientRect();

    let percent = (event.clientX - rect.left) / rect.width;
    percent = Math.max(0, Math.min(1, percent));

    const newPosition = percent * currentDuration;

    currentPosition = newPosition;
    updateProgressBar();

    fetch('/control/seek', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            position_ms: newPosition
        })
    })
    .then(response => response.json())
    .then(data => {
        setTimeout(() => { isUserSeeking = false; }, 1500);
    })
    .catch(err => {
        isUserSeeking = false;
        console.error('Seek hatası:', err);
    });
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().then(() => {
            document.body.classList.add('fullscreen-mode');
        }).catch(err => console.error('Tam ekran hatası:', err));
    } else {
        document.exitFullscreen().then(() => {
            document.body.classList.remove('fullscreen-mode');
        });
    }
}

function control(action) {
    fetch('/control/' + action, { method: 'POST' })
        .catch(err => console.error('Kontrol hatası:', err));
}

document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement) {
        document.body.classList.remove('fullscreen-mode');
    }
});