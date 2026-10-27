shader_type spatial;
// The gracht: two scrolling ripple normal maps, colour deepening away from the quays, a band of
// foam/scum against both quay walls, glossy enough to catch the sky. Local space of a flat box
// centred on the water (Blender's "Gracht_Water"): x along the canal, z across it.
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform vec3 deep : source_color = vec3(0.09, 0.17, 0.13);
uniform vec3 shallow : source_color = vec3(0.2, 0.3, 0.22);
uniform vec3 foam_col : source_color = vec3(0.78, 0.82, 0.74);
uniform float half_width = 4.0;     // metres from the centre line to a quay wall
uniform sampler2D ripples_a : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D ripples_b : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D scum : filter_linear_mipmap, repeat_enable;

varying vec3 lp;

void vertex() {
	lp = VERTEX;
}

void fragment() {
	vec2 uv = lp.xz * 0.11;
	vec3 na = texture(ripples_a, uv + TIME * vec2(0.025, 0.008)).rgb;
	vec3 nb = texture(ripples_b, uv * 1.9 + TIME * vec2(-0.018, 0.03)).rgb;
	NORMAL_MAP = normalize(na + nb - 1.0) * 0.5 + 0.5;
	NORMAL_MAP_DEPTH = 0.7;
	float edge = half_width - abs(lp.z);
	float n = texture(scum, lp.xz * 0.35 + TIME * vec2(0.01, 0.0)).r;
	float foam = smoothstep(0.55, 0.05, edge + (n - 0.5) * 0.5);
	float centre = smoothstep(0.4, half_width, edge);
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 4.0);
	vec3 water = mix(shallow, deep, centre);
	ALBEDO = mix(water, foam_col, foam * 0.75);
	ROUGHNESS = mix(0.03, 0.7, foam);
	METALLIC = 0.0;
	SPECULAR = mix(0.35, 0.8, fres);
}
