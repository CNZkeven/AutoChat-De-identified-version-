// 图片配置文件 - 用户可自行修改路径
const imageConfig = {
    // 主页背景图 (尺寸建议: 1920x1080)
    homeBackground: 'images/037b46756f83c2f61e04e7368e2feb12.jpg',
    
    // 智能体卡片背景图
    agentCards: {
        exploration: 'images/1f70d339b0b9eda3f95387bc102b4644_0.jpg',
        evaluation: 'images/3abee1adc3279109c8ede1004eba52c8_0.jpg',
        ideological: 'images/4e95f6fa4fbda42e8482ba06506284ce_0.jpg',
        course: 'images/a43168df1330ad63a3cb3f63563bb2d8_720.jpg',
        task: 'images/dff83e09cf9a55b16ba337ed1c51e1a8_0.jpg',
        competition: 'images/eaacf4c0a0bdadbdb1cadbf40773ce48.jpg'
    },
    
    // 主导航栏背景图 (尺寸建议: 1920x100)
    mainNav: 'images/037b46756f83c2f61e04e7368e2feb12.jpg',
    // 智能体导航背景图配置 (尺寸建议: 1920x100)
    navbar: {
        exploration: 'images/1f70d339b0b9eda3f95387bc102b4644_0.jpg',
        evaluation: 'images/3abee1adc3279109c8ede1004eba52c8_0.jpg',
        ideological: 'images/4e95f6fa4fbda42e8482ba06506284ce_0.jpg',
        course: 'images/a43168df1330ad63a3cb3f63563bb2d8_720.jpg',
        task: 'images/dff83e09cf9a55b16ba337ed1c51e1a8_0.jpg',
        competition: 'images/eaacf4c0a0bdadbdb1cadbf40773ce48.jpg'
    },

    // 标题背景图配置 (尺寸建议: 1920x100)
    titleBanner: {
        ideological: 'images/037b46756f83c2f61e04e7368e2feb12.jpg',
        evaluation: 'images/6476cbf5ac054be7d8d0b82690254534.jpg', 
        task: 'images/dff83e09cf9a55b16ba337ed1c51e1a8_0.jpg',
        exploration: 'images/1f70d339b0b9eda3f95387bc102b4644_0.jpg',
        competition: 'images/e469a5684820f4c1182de3da117fe044.jpg',
        course: 'images/3abee1adc3279109c8ede1004eba52c8_0.jpg'
    },

    // 智能体卡片背景图配置 (尺寸建议: 400x300)
    cards: {
        ideological: 'images/037b46756f83c2f61e04e7368e2feb12.jpg',
        evaluation: 'images/6476cbf5ac054be7d8d0b82690254534.jpg',
        task: 'images/dff83e09cf9a55b16ba337ed1c51e1a8_0.jpg',
        exploration: 'images/1f70d339b0b9eda3f95387bc102b4644_0.jpg',
        competition: 'images/e469a5684820f4c1182de3da117fe044.jpg',
        course: 'images/3abee1adc3279109c8ede1004eba52c8_0.jpg'
    }
};

// 应用图片配置的函数
function applyImageConfig() {
    // 获取当前页面智能体类型
    const path = window.location.pathname.split('/').pop();
    const agent = path.replace('.html', '');

    // 设置主页背景
    if (path === 'index.html' && imageConfig.homeBackground) {
        console.log('[背景图调试] 正在加载主页背景:', imageConfig.homeBackground);
        const homeBg = document.createElement('style');
        homeBg.innerHTML = `
            body {
                background-image: url('${imageConfig.homeBackground}');
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }
        `;
        document.head.appendChild(homeBg);
    }
    
    // 设置导航栏背景
    if (imageConfig.navbar[agent]) {
        console.log('[导航栏背景] 正在加载:', agent, imageConfig.navbar[agent]);
        const navLinks = document.querySelectorAll('.nav-links a');
        navLinks.forEach(link => {
            if (link.getAttribute('href').includes(agent)) {
                console.log('[导航栏背景] 应用到链接:', link.getAttribute('href'));
                console.log('[导航栏背景] 完整图片路径:', 
                    new URL(imageConfig.navbar[agent], window.location.href).href);
                
                link.style.backgroundImage = `url('${imageConfig.navbar[agent]}')`;
                link.style.backgroundSize = 'cover';
                link.style.backgroundPosition = 'center';
                link.style.backgroundRepeat = 'no-repeat';
                
                // 测试图片是否可加载
                const img = new Image();
                img.onload = () => console.log('[图片加载] 成功:', imageConfig.navbar[agent]);
                img.onerror = () => console.error('[图片加载] 失败:', imageConfig.navbar[agent]);
                img.src = imageConfig.navbar[agent];
            }
        });
    }

    // 设置标题背景
    if (imageConfig.titleBanner[agent]) {
        console.log('[背景图调试] 正在加载:', imageConfig.titleBanner[agent]);
        const banner = document.createElement('style');
        banner.innerHTML = `
            .chat-section::before {
                background-image: url('${imageConfig.titleBanner[agent]}');
                background-size: cover;
                background-position: center;
            }
        `;
        document.head.appendChild(banner);
    }

    // 设置卡片背景
    if (imageConfig.cards[agent]) {
        const cardImages = document.querySelectorAll('.agent-image');
        cardImages.forEach(img => {
            img.style.backgroundImage = `url('${imageConfig.cards[agent]}')`;
        });
    }
}

// 页面加载完成后应用配置
document.addEventListener('DOMContentLoaded', applyImageConfig);
