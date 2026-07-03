// frontend/atmosphere.js

class Particle {
    constructor(config, width, height) {
        this.canvasWidth = width;
        this.canvasHeight = height;
        this.reset(config, true);
    }

    reset(config, randomY = false) {
        this.x = Math.random() * this.canvasWidth;
        this.y = randomY ? Math.random() * this.canvasHeight : (config.vy > 0 ? -10 : this.canvasHeight + 10);
        this.vx = config.vx + (Math.random() - 0.5) * (config.vxVariance || 0);
        this.vy = config.vy + (Math.random() - 0.5) * (config.vyVariance || 0);
        this.size = config.size + Math.random() * (config.sizeVariance || 0);
        this.opacity = config.baseOpacity || 1;
        this.color = config.color;
        this.life = 0;
        this.maxLife = config.maxLife || 1000;
        this.fadeRate = config.fadeRate || 0;
    }

    update(config) {
        this.x += this.vx;
        this.y += this.vy;
        this.life++;
        if (this.fadeRate) this.opacity -= this.fadeRate;

        // Reset if out of bounds or dead
        if (this.x < -20 || this.x > this.canvasWidth + 20 || 
            this.y < -20 || this.y > this.canvasHeight + 20 ||
            this.opacity <= 0 || this.life >= this.maxLife) {
            this.reset(config);
        }
    }

    draw(ctx) {
        ctx.save();
        ctx.globalAlpha = Math.max(0, this.opacity);
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }
}

const WEATHER_CONFIGS = {
    'Clear': {
        color: '#c9a96e', baseOpacity: 0.6,
        vx: 0.2, vy: -0.3, vxVariance: 0.1, vyVariance: 0.2,
        size: 1.5, sizeVariance: 1,
        maxParticles: 50, spawnRate: 1, fadeRate: 0.002,
        bgColor: '#241711' // default
    },
    'Rain': {
        color: '#a0b4d4', baseOpacity: 0.8,
        vx: -3, vy: 18, vxVariance: 1, vyVariance: 4,
        size: 1.2, sizeVariance: 0.5,
        maxParticles: 300, spawnRate: 15, fadeRate: 0,
        bgColor: '#1a1a24'
    },
    'Storm': {
        color: '#d1d5db', baseOpacity: 0.9,
        vx: -5, vy: 25, vxVariance: 2, vyVariance: 5,
        size: 1.5, sizeVariance: 0.5,
        maxParticles: 500, spawnRate: 25, fadeRate: 0,
        bgColor: '#0d0d15'
    },
    'Drought': {
        color: '#d4884a', baseOpacity: 0.5,
        vx: 0, vy: -1.5, vxVariance: 0.5, vyVariance: 0.5,
        size: 2, sizeVariance: 1,
        maxParticles: 100, spawnRate: 3, fadeRate: 0.005,
        bgColor: '#2e1e0a'
    },
    'Fog': {
        color: '#ffffff', baseOpacity: 0.04,
        vx: 0.5, vy: 0, vxVariance: 0.2, vyVariance: 0.1,
        size: 50, sizeVariance: 30,
        maxParticles: 40, spawnRate: 1, fadeRate: 0.001,
        bgColor: '#2a2520'
    }
};

window.Atmosphere = {
    canvas: null,
    ctx: null,
    particles: [],
    currentWeather: 'Clear',
    width: 0,
    height: 0,
    animationFrameId: null,

    init() {
        this.canvas = document.getElementById('atmosphere-canvas');
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        
        this.resize();
        window.addEventListener('resize', () => this.resize());
        
        this.setWeather('Clear');
        this.loop();
    },

    resize() {
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
    },

    setWeather(weather) {
        if (!WEATHER_CONFIGS[weather]) weather = 'Clear';
        this.currentWeather = weather;
        const config = WEATHER_CONFIGS[weather];
        
        document.body.style.backgroundColor = config.bgColor;
        document.body.style.transition = 'background-color 2s ease';
        
        if (this.particles.length > config.maxParticles) {
            this.particles = this.particles.slice(0, config.maxParticles);
        }
        
        this.particles.forEach(p => p.reset(config, true));
    },

    setOmen(omen) {
        const overlay = document.getElementById('omen-overlay');
        if (!overlay) return;

        overlay.className = 'omen-overlay'; // Reset (handles 'None' / null)
        if (omen === 'Blood Moon') overlay.classList.add('omen-blood-moon');
        else if (omen === 'Eclipse') overlay.classList.add('omen-eclipse');
        else if (omen === 'Comet') overlay.classList.add('omen-comet');
    },

    // Each intervention type has a few interchangeable flourishes; one is picked at
    // random per cast so repeated interventions never look identical.
    SPECTACLE_VARIANTS: {
        miracle: ['spectacle-miracle', 'spectacle-miracle-bloom', 'spectacle-miracle-dawn'],
        smite:   ['spectacle-smite', 'spectacle-smite-crack', 'spectacle-smite-burst'],
        nudge:   ['spectacle-nudge', 'spectacle-nudge-veil', 'spectacle-nudge-wisp'],
    },

    playSpectacle(type) {
        const overlay = document.getElementById('spectacle-overlay');
        if (!overlay) return;

        const variants = this.SPECTACLE_VARIANTS[type] || this.SPECTACLE_VARIANTS.nudge;
        const variant = variants[Math.floor(Math.random() * variants.length)];

        overlay.className = 'spectacle-overlay'; // Reset
        void overlay.offsetWidth; // Force reflow to restart animation
        overlay.classList.add(variant);

        if (type === 'smite') {
            document.body.classList.add('shake-screen');
            setTimeout(() => document.body.classList.remove('shake-screen'), 500);
        }

        setTimeout(() => {
            overlay.className = 'spectacle-overlay hidden';
        }, 1600);
    },

    loop() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        
        const config = WEATHER_CONFIGS[this.currentWeather];
        
        if (this.particles.length < config.maxParticles && Math.random() < 0.5) {
            for(let i = 0; i < config.spawnRate; i++) {
                if (this.particles.length < config.maxParticles) {
                    this.particles.push(new Particle(config, this.width, this.height));
                }
            }
        }
        
        this.particles.forEach(p => {
            p.update(config);
            p.draw(this.ctx);
        });
        
        if (this.currentWeather === 'Storm' && Math.random() < 0.01) {
            this.ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
            this.ctx.fillRect(0, 0, this.width, this.height);
        }
        
        this.animationFrameId = requestAnimationFrame(() => this.loop());
    }
};
