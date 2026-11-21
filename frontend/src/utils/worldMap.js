import * as echarts from "echarts";

let registerPromise = null;

export function ensureWorldMap() {
  if (!registerPromise) {
    registerPromise = fetch("https://cdn.jsdelivr.net/npm/echarts@4.9.0/map/json/world.json")
      .then((res) => res.json())
      .then((geoJson) => {
        echarts.registerMap("world", geoJson);
      });
  }
  return registerPromise;
}
