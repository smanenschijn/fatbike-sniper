shader_type canvas_item;
// Bullet-time grade: cool desaturation with warm highlights, chromatic fringe, pulsing vignette,
// film grain, radial speed lines and a "time ripple" shockwave when it kicks in.

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform float amount = 0.0;     // 0..1 strength of the look
uniform float wave = -1.0;      // shockwave radius (screen heights); < 0 = off
uniform float time_s = 0.0;

void fragment() {
	vec2 uv = SCREEN_UV;
	vec2 d = uv - vec2(0.5);
	float aspect = SCREEN_PIXEL_SIZE.y / SCREEN_PIXEL_SIZE.x;
	vec2 da = vec2(d.x * aspect, d.y);
	float r = length(da);

	// time ripple: a refracting ring racing outwards
	if (wave >= 0.0) {
		float w = r - wave;
		float ring = exp(-w * w * 260.0) * (1.0 - clamp(wave / 1.3, 0.0, 1.0));
		uv -= normalize(d + vec2(1e-5)) * ring * 0.035;
	}

	vec2 off = d * 0.016 * amount;
	vec4 base = textureLod(screen_tex, uv, 0.0);
	vec3 col = vec3(textureLod(screen_tex, uv + off, 0.0).r, base.g, textureLod(screen_tex, uv - off, 0.0).b);

	float l = dot(col, vec3(0.2126, 0.7152, 0.0722));
	vec3 grade = mix(vec3(l) * vec3(0.78, 0.97, 1.14), col, 0.28);
	grade = mix(grade, grade * vec3(1.18, 0.98, 0.78), smoothstep(0.55, 1.0, l));
	col = mix(col, grade * 0.92, amount);

	// speed lines near the edges
	float ang = atan(da.y, da.x);
	float lane = floor(ang * 38.0 + floor(time_s * 3.0) * 0.37);
	float streak = step(0.86, fract(sin(lane * 91.7) * 437.58)) * smoothstep(0.42, 0.95, r);
	col = mix(col, vec3(0.78, 0.96, 1.0), streak * 0.16 * amount);

	// heartbeat vignette
	float beat = pow(0.5 + 0.5 * sin(time_s * 7.0), 6.0);
	col *= 1.0 - amount * smoothstep(0.28, 0.85, r) * (0.72 + 0.12 * beat);

	// film grain
	float n = fract(sin(dot(uv * (time_s + 1.0), vec2(12.9898, 78.233))) * 43758.5453);
	col += (n - 0.5) * 0.05 * amount;

	COLOR = vec4(col, 1.0);
}
