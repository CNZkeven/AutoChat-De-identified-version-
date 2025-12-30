// 图片配置文件 - 用户可自行修改路径
const imageConfig = {
    // 主页背景图 (尺寸建议: 1920x1080)
    homeBackground: 'static/images/037b46756f83c2f61e04e7368e2feb12.jpg',   
    // 智能体卡片背景图
    agentCards: {   
        course: 'static/images/a43168df1330ad63a3cb3f63563bb2d8_720.jpg',
        task: 'static/images/dff83e09cf9a55b16ba337ed1c51e1a8_0.jpg',  
    },
    
    // 主导航栏背景图 (尺寸建议: 1920x100)
    mainNav: 'static/images/037b46756f83c2f61e04e7368e2feb12.jpg',
    // 智能体导航背景图配置 (尺寸建议: 1920x100)
    navbar: {
      
        course: 'static/images/a43168df1330ad63a3cb3f63563bb2d8_720.jpg',
        task: 'static/images/dff83e09cf9a55b16ba337ed1c51e1a8_0.jpg',
        
    },

    // 标题背景图配置 (尺寸建议: 1920x100)
    titleBanner: {
        task: 'static/images/dff83e09cf9a55b16ba337ed1c51e1a8_0.jpg',       
        course: 'static/images/3abee1adc3279109c8ede1004eba52c8_0.jpg'
    },

    // 智能体卡片背景图配置 (尺寸建议: 400x300)
    cards: {
       
        task: 'static/images/dff83e09cf9a55b16ba337ed1c51e1a8_0.jpg',
        
        course: 'static/images/3abee1adc3279109c8ede1004eba52c8_0.jpg'
    }
};

// 将相对路径规范为以 /static/ 开头的绝对 URL（兼容 Flask）
function resolveStaticPath(p) {
    if (!p) return null;
    try {
        // 如果已经是完整 URL，则直接返回
        return new URL(p).href;
    } catch (e) {
        // 否则确保以 /static/ 开头并返回带 origin 的绝对地址
        const cleaned = p.replace(/^\/+/, ''); // 去掉开头斜杠
        // 如果用户已经给出 static/... 则只加前缀，否则也能处理 images/...
        const prefixRemoved = cleaned.startsWith('static/') ? cleaned.slice(7) : cleaned;
        return `${window.location.origin}/static/${prefixRemoved}`;
    }
}

// 更稳健地获取 agent：支持 '/', '/task', '/course', '/xxx.html' 等
function getAgentFromPath() {
    let p = window.location.pathname || '/';
    p = p.replace(/^\/+|\/+$/g, ''); // 去掉首尾斜杠
    if (!p) return 'index';
    const parts = p.split('/');
    const last = parts[parts.length - 1];
    return last.endsWith('.html') ? last.replace(/\.html$/, '') : last;
}

function applyImageConfig() {
    try {
        const agent = getAgentFromPath();

        // 主页背景（支持 root 路由）
        if (agent === 'index' && imageConfig.homeBackground) {
            const url = resolveStaticPath(imageConfig.homeBackground);
            if (url) {
                const s = document.createElement('style');
                s.innerHTML = `
                    body {
                        background-image: url('${url}');
                        background-size: cover;
                        background-position: center;
                        background-attachment: fixed;
                    }
                `;
                document.head.appendChild(s);
                console.log('[image-config] 应用主页背景:', url);
            }
        }

        // 导航栏背景（防护性检查）
        if (imageConfig.navbar && imageConfig.navbar[agent]) {
            const navUrl = resolveStaticPath(imageConfig.navbar[agent]);
            const navLinks = document.querySelectorAll('.nav-links a');
            if (navLinks && navLinks.length) {
                navLinks.forEach(link => {
                    const href = link.getAttribute('href') || '';
                    const match = (agent === 'index' && (href === '/' || href.includes('index'))) || href.includes(agent);
                    if (match) {
                        link.style.backgroundImage = `url('${navUrl}')`;
                        link.style.backgroundSize = 'cover';
                        link.style.backgroundPosition = 'center';
                        link.style.backgroundRepeat = 'no-repeat';
                        const img = new Image();
                        img.onload = () => console.log('[image-config] 导航图片加载成功:', navUrl);
                        img.onerror = () => console.error('[image-config] 导航图片加载失败:', navUrl);
                        img.src = navUrl;
                    }
                });
            }
        }

        // 标题横幅背景
        if (imageConfig.titleBanner && imageConfig.titleBanner[agent]) {
            const bannerUrl = resolveStaticPath(imageConfig.titleBanner[agent]);
            const s = document.createElement('style');
            s.innerHTML = `
                .chat-section::before {
                    background-image: url('${bannerUrl}');
                    background-size: cover;
                    background-position: center;
                }
            `;
            document.head.appendChild(s);
            console.log('[image-config] 应用标题横幅:', bannerUrl);
        }

        // 卡片背景（按每个卡片的类型设置，不再只依赖当前路由）
        // 为每个 .agent-card 单独设置背景，优先使用 data-agent 属性，其次根据 href 推断（支持 course/task）
        const cardEls = document.querySelectorAll('.agent-card');
        if (cardEls && cardEls.length) {
            cardEls.forEach(card => {
                try {
                    let type = card.dataset.agent || '';
                    if (!type) {
                        const href = card.getAttribute('href') || '';
                        if (href.includes('course')) type = 'course';
                        else if (href.includes('task')) type = 'task';
                    }

                    // 优先使用 cards 配置，其次回退到 agentCards 配置
                    let src = (imageConfig.cards && imageConfig.cards[type]) ? imageConfig.cards[type]
                              : (imageConfig.agentCards && imageConfig.agentCards[type]) ? imageConfig.agentCards[type]
                              : null;
                    if (!src) return;
                    const url = resolveStaticPath(src);
                    const imgEl = card.querySelector('.agent-image') || card;
                    imgEl.style.backgroundImage = `url('${url}')`;
                    imgEl.style.backgroundSize = 'cover';
                    imgEl.style.backgroundPosition = 'center';
                    imgEl.style.backgroundRepeat = 'no-repeat';
                } catch (e) {
                    console.error('[image-config] 设置卡片背景失败', e);
                }
            });
        }
    } catch (err) {
        console.error('[image-config] applyImageConfig 错误:', err);
    }
}

document.addEventListener('DOMContentLoaded', applyImageConfig);
