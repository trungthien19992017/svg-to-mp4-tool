import {createEpisode} from "../modules/episode-runtime.js";
import {evaluate} from "../motions/motion-library.js";
export function createScene(context) {
  return createEpisode(context, {"rig": {"version": "robot-demo-v1", "joints": {"body": {"nodeId": "body", "pivot": [360, 800]}, "head": {"nodeId": "head", "pivot": [360, 490]}, "leftArm": {"nodeId": "arm-left", "pivot": [232, 570]}, "rightArm": {"nodeId": "arm-right", "pivot": [487, 570]}}, "anchors": {"leftSole": [310, 1010], "rightSole": [410, 1010]}}, "pose": {"id": "idle", "rigVersion": "robot-demo-v1", "status": "Supported", "rotations": {}}, "expression": {"id": "happy", "nodeId": "face-happy", "rigVersion": "robot-demo-v1", "status": "Supported"}, "expressionNodes": ["face-neutral", "face-happy"], "duration": 4, "assetId": "actor-art"}, evaluate);
}
