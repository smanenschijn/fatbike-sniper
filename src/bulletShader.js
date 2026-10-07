/** Bullet-time grade: cool desaturation, warm highlights, chromatic fringe and a heavy vignette. */
export const BulletTimeShader = {
  uniforms: { tDiffuse: { value: null }, amount: { value: 0 } },
  vertexShader: /* glsl */`
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse;
    uniform float amount;
    varying vec2 vUv;
    void main() {
      vec2 d = vUv - 0.5;
      float r = length(d);
      vec2 off = d * 0.014 * amount;
      vec4 base = texture2D(tDiffuse, vUv);
      vec3 col = vec3(texture2D(tDiffuse, vUv + off).r, base.g, texture2D(tDiffuse, vUv - off).b);
      float l = dot(col, vec3(0.2126, 0.7152, 0.0722));
      vec3 grade = mix(vec3(l) * vec3(0.8, 0.98, 1.12), col, 0.3);
      grade = mix(grade, grade * vec3(1.15, 0.97, 0.78), smoothstep(0.6, 2.5, l));
      col = mix(col, grade * 0.82, amount);
      col *= 1.0 - amount * smoothstep(0.3, 0.8, r) * 0.8;
      gl_FragColor = vec4(col, base.a);
    }`,
};
