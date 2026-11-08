/**
 * Phase 03 / reusable deterministic GSAP timeline-driven motion.
 * Studio API usage: context.timeline(), context.gsap; no autonomous tweens or callbacks.
 * Source V4 status: motions are TECHNICAL PROTOTYPES, not approved animation art.
 */
const EPS = 1e-8;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const lerp = (a, b, t) => a + (b - a) * t;
const CHANNELS = Object.freeze({
    idle: ['head-y'],
    blink: ['blink'],
    breathe: ['neck-y'],
    lookAt: ['head-rotation'],
    headTilt: ['head-rotation'],
    happyReaction: ['expression', 'head-y'],
    surprisedReaction: ['expression', 'head-y'],
    sadReaction: ['expression', 'head-rotation'],
    reach: ['arm-near'],
    touch: ['arm-near'],
    release: ['arm-near'],
    walk: ['actor-x', 'gait', 'arm-near'],
    stopWalking: ['gait', 'arm-near']
});
const EASINGS = Object.freeze({
    none: t => t,
    'sine.inOut': t => -(Math.cos(Math.PI * t) - 1) / 2,
    'sine.out': t => Math.sin(Math.PI * t / 2),
    'power1.inOut': t => t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2,
    'power2.out': t => 1 - Math.pow(1 - t, 3),
    'power2.inOut': t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
});
const ALLOWED_EXPRESSIONS = new Set([
    'shy', 'loving', 'worried', 'crying', 'sleepy', 'touched',
    'default', 'cheerful', 'sad', 'surprised', 'content', 'pleased'
]);

export function actionChannels(type) {
    if (!CHANNELS[type]) throw new Error('Unknown motion action: ' + type);
    return [...CHANNELS[type]];
}
export function createMotionComposer({duration, actors, gsap = null}) {
    if (!Number.isFinite(duration) || duration <= 0) throw new Error('Finite duration required');
    const ids = Object.keys(actors);
    if (!ids.length) throw new Error('At least one actor required');
    const schedule = [];
    let serial = 0;
    let finalized = false;

    function add(type, actor, start, actionDuration, options = {}) {
        if (finalized) throw new Error('Motion schedule already finalized');
        actionChannels(type);
        if (!actors[actor]) throw new Error('Unknown actor ' + actor);
        if (![start, actionDuration].every(Number.isFinite) || start < 0 || actionDuration <= 0 || start + actionDuration > duration + EPS) {
            throw new Error('Invalid action interval ' + type);
        }
        if (['happyReaction', 'surprisedReaction', 'sadReaction'].includes(type)) {
            const target = options.expression || ({happyReaction:'pleased', surprisedReaction:'surprised', sadReaction:'sad'})[type];
            if (!ALLOWED_EXPRESSIONS.has(target)) throw new Error('Unknown authored expression ' + target);
        }
        if (['reach', 'touch', 'release'].includes(type)) {
            if (!['L', 'R'].includes(options.arm) || !options.targetAngles) throw new Error('Authored arm/targetAngles required');
            for (const key of ['upper','forearm','hand']) {
                if (!Number.isFinite(options.targetAngles[key])) throw new Error('Non-finite joint target ' + key);
            }
        }
        const channels = actionChannels(type);
        const end = start + actionDuration;
        for (const previous of schedule) {
            if (previous.actor !== actor || !channels.some(channel => previous.channels.includes(channel))) continue;
            if (start < previous.end - EPS && previous.start < end - EPS) {
                throw new Error('Conflicting motion channels: ' + actor + ' ' + type + ' / ' + previous.type +
                    ' (' + channels.filter(channel => previous.channels.includes(channel)).join(',') + ')');
            }
        }
        const action = Object.freeze({id: options.id || type + '-' + (++serial),
            type, actor, start, end, duration: actionDuration,
            easing: options.easing || 'sine.inOut', channels, options: {...options}});
        if (!EASINGS[action.easing] && !(gsap && typeof gsap.parseEase === 'function')) {
            throw new Error('Unsupported easing: ' + action.easing);
        }
        schedule.push(action);
        return action;
    }
    function finalize() {
        schedule.sort((a,b) => a.start - b.start || a.end - b.end || a.id.localeCompare(b.id));
        finalized = true;
        return schedule.slice();
    }
    function ease(action, p) {
        const fn = gsap && typeof gsap.parseEase === 'function' ? gsap.parseEase(action.easing) : EASINGS[action.easing];
        if (typeof fn !== 'function') throw new Error('Unknown easing ' + action.easing);
        return fn(clamp(p, 0, 1));
    }
    function evaluate(t) {
        if (!finalized) finalize();
        const time = clamp(Number.isFinite(t) ? t : 0, 0, duration);
        const result = {};
        for (const [id, actor] of Object.entries(actors)) {
            result[id] = {
                x: actor.x, y: actor.y, scale: actor.scale,
                headY: 0, headRotation: 0, neckY: 0, bodyY: 0,
                expression: 'default', blink: 0, gait: 0, gaitTime: time,
                armL: {upper:0,forearm:0,hand:0}, armR: {upper:0,forearm:0,hand:0}
            };
        }
        for (const action of schedule) {
            if (time + EPS < action.start) continue;
            const state = result[action.actor];
            const o = action.options;
            const p = clamp((time - action.start) / action.duration, 0, 1);
            const q = ease(action, p);
            const within = time <= action.end + EPS;
            switch (action.type) {
                case 'idle': {
                    // Neutral head bob, finite and returns to rest at action end.
                    state.headY = within ? Math.sin(2 * Math.PI * p * (o.cycles || 1)) * (o.amplitude ?? 1.5) * Math.sin(Math.PI * p) : 0;
                    break;
                }
                case 'breathe': {
                    state.neckY = within ? Math.sin(2 * Math.PI * (time - action.start) / (o.period || 2.8)) * (o.amplitude ?? 1.4) * Math.sin(Math.PI * p) : 0;
                    break;
                }
                case 'blink': {
                    state.blink = within ? Math.sin(Math.PI * p) : 0;
                    break;
                }
                case 'lookAt':
                case 'headTilt': {
                    state.headRotation = lerp(o.from ?? 0, o.to ?? 0, q);
                    break;
                }
                case 'happyReaction':
                case 'surprisedReaction': {
                    state.expression = o.expression || (action.type === 'happyReaction' ? 'pleased' : 'surprised');
                    state.headY = lerp(o.fromY ?? 0, o.toY ?? (action.type === 'happyReaction' ? -2 : -5), q);
                    break;
                }
                case 'sadReaction': {
                    state.expression = o.expression || 'sad';
                    state.headRotation = lerp(o.from ?? 0, o.to ?? 6, q);
                    break;
                }
                case 'reach':
                case 'touch':
                case 'release': {
                    const from = o.fromFactor ?? (action.type === 'reach' ? 0 : action.type === 'release' ? 1 : .92);
                    const to = o.toFactor ?? (action.type === 'reach' ? .92 : action.type === 'release' ? 0 : 1);
                    const factor = lerp(from, to, q);
                    const key = o.arm === 'L' ? 'armL' : 'armR';
                    state[key] = {
                        upper: o.targetAngles.upper * factor,
                        forearm: o.targetAngles.forearm * factor,
                        hand: o.targetAngles.hand * factor
                    };
                    break;
                }
                case 'walk': {
                    state.x = lerp(o.fromX ?? actors[action.actor].x, o.toX ?? actors[action.actor].x, q);
                    const fadeIn = clamp(p / (o.ramp || .16), 0, 1);
                    state.gait = within ? fadeIn : 1;
                    break;
                }
                case 'stopWalking': {
                    state.gait = lerp(o.fromGait ?? 1, 0, q);
                    break;
                }
                default: throw new Error('Missing action implementation ' + action.type);
            }
        }
        for (const state of Object.values(result)) {
            state.bodyY = -3.5 * Math.abs(Math.sin(time * Math.PI * 2 * 1.6)) * state.gait;
        }
        return result;
    }
    return {add, finalize, evaluate, get actions() {return schedule.slice();}, duration};
}

/** One GSAP-controlled absolute clock; all SVG state is a pure function of that clock. */
export function createTimelineMotion(context, composer, renderFrame) {
    const duration = composer.duration;
    const clock = {time:0};
    const timeline = context.timeline();
    timeline.fromTo(clock, {time:0}, {time:duration, duration, ease:'none', immediateRender:false}, 0);
    let disposed = false;
    function seek(time) {
        if (disposed) return;
        const t = clamp(Number.isFinite(time) ? time : 0, 0, duration);
        timeline.time(t, true); // callback suppression safe: no visual callbacks exist.
        renderFrame(composer.evaluate(clock.time), clock.time);
    }
    seek(0);
    return {
        duration, timeline, seek,
        reset() {if (!disposed) {timeline.pause(0); clock.time = 0; seek(0);}},
        dispose() {if (!disposed) {disposed = true; timeline.kill();}}
    };
}
