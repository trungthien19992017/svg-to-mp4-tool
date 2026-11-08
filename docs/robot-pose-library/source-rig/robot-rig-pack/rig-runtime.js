export function applyPose(root,rig,pose={}) {
 for(const n of rig.nodes){const el=root.querySelector('[data-part="'+n.id+'"]');if(!el)throw new Error('Missing part '+n.id);const a=Number(pose[n.id]||0);if(!Number.isFinite(a))throw new Error('Invalid angle');el.setAttribute('transform','translate('+n.mount.join(' ')+') rotate('+a+')');}
}
export function worldAnchor(rig,pose,id,key){
 const nodes=Object.fromEntries(rig.nodes.map(n=>[n.id,n]));let n=nodes[id];if(!n||!n.anchors[key])throw new Error('Missing anchor');let p=n.anchors[key].slice();while(n){const a=(pose[n.id]||0)*Math.PI/180,c=Math.cos(a),s=Math.sin(a);p=[c*p[0]-s*p[1]+n.mount[0],s*p[0]+c*p[1]+n.mount[1]];n=nodes[n.parent];}return p;
}
