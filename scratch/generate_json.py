# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

beats = [
    {
        "text": "Chương 10: Không Gian Không Tên. Họ bắt đầu đi xuống lòng đất vào lúc sáng sớm ngày mười hai tháng chín — ",
        "beat_action": "Establishing the scene at sunrise",
        "description": "{RÌA ZONE 4}, wide/establishing shot, eye-level, {Tiểu Kỳ} sits on a rusty metal guardrail at the edge of {RÌA ZONE 4} with her worn {Ba lô} at her feet, looking east, while {Hùng} stands nearby on the technical road. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Wide establishing shot, eye-level angle. Lens: 24mm wide-angle lens, deep focus. Lighting: early morning golden hour, weak orange sunlight filtering through thick gray industrial air filters, casting soft shadows. Composition: rule of thirds, with the rusty metal guardrail stretching along the road, {Tiểu Kỳ} sitting on it on the left, her canvas {Ba lô} on the concrete ground, {Hùng} standing in the midground on the right, his hand near his kaki coat pocket. Background: the hazy skyline of Omega-7 under a gray morning dust haze. Mood: quiet, tense, mysterious, futuristic industrial.",
        "motion_prompt": "Camera movement: slow panning right, establishing the industrial road. Focus: deep focus on both characters. Light: soft orange light shifts as dawn breaks. Subject motion: {Tiểu Kỳ} looking towards the horizon, {Hùng} standing still.",
        "ref_entity_names": ["RÌA ZONE 4", "Tiểu Kỳ", "Ba lô", "Hùng"],
        "key_phrases": ["Không Gian Không Tên", "sáng sớm ngày mười hai tháng chín"]
    },
    {
        "text": "bốn ngày sau khi Tiểu Kỳ đột ngột xuất hiện ở cửa căn hộ của anh giữa đêm muộn hai giờ sáng, và ba ngày kể từ khi Sable mở lối terminal tự ý thức đầu tiên để chạm vào nhận thức của anh. ",
        "beat_action": "Waiting at the edge of Zone 4",
        "description": "{RÌA ZONE 4}, full shot, low angle, {Hùng} stands near the rusty metal guardrail, looking down at {Tiểu Kỳ} who remains sitting with her worn {Ba lô}. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Full shot, low angle. Lens: 35mm lens, deep focus. Lighting: soft morning daylight, dim cool tones with a hint of warm orange backlighting from the sunrise. Composition: low-angle perspective looking up at {Hùng} standing in his kaki coat, with {Tiểu Kỳ} sitting on the guardrail in the foreground, her canvas {Ba lô} beside her feet. {Hùng}'s pockets show outlines of a {Sổ tay}, a {Đèn pin}, and a {Thiết bị đo tần số}. Background: rusty steel structures of the technical road at {RÌA ZONE 4}. Mood: reflective, tense, sci-fi mystery.",
        "motion_prompt": "Camera movement: static lock-off, no camera move. Light: slight drifting of gray particles in the morning air. Subject motion: {Hùng} adjusts his position slightly, keeping his eyes on the horizon.",
        "ref_entity_names": ["RÌA ZONE 4", "Hùng", "Tiểu Kỳ", "Ba lô", "Sổ tay", "Đèn pin", "Thiết bị đo tần số"],
        "key_phrases": ["Tiểu Kỳ đột ngột xuất hiện", "Sable mở lối terminal"]
    },
    {
        "text": "Bản tin nhắn của Tiểu Kỳ gửi vào tối hôm trước ngắn gọn đến mức tối giản: “Anh sẵn sàng chưa?” Hùng chỉ phản hồi lại hai chữ: “Sáng mai.” Giữa họ đã hình thành một kiểu thỏa thuận ngầm không lời. ",
        "beat_action": "Subtle interaction in silence",
        "description": "{RÌA ZONE 4}, medium shot, high angle, {Hùng} stands near the guardrail where {Tiểu Kỳ} sits, both looking ahead in silence. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Medium shot, high angle. Lens: 50mm portrait lens, shallow depth of field. Lighting: soft golden key light from the side, cool grey fill light. Composition: high angle looking down at {Tiểu Kỳ} sitting on the rusty guardrail, with {Hùng} standing close by, his hands in his pockets. The worn {Ba lô} is at the bottom of the frame. Mood: quiet understanding, unresolved tension, industrial sci-fi.",
        "motion_prompt": "Camera movement: slow dolly-in towards {Tiểu Kỳ} and {Hùng}. Light: morning shadows stretching across the technical road. Subject motion: {Hùng} turns his head slightly toward {Tiểu Kỳ}.",
        "ref_entity_names": ["RÌA ZONE 4", "Hùng", "Tiểu Kỳ", "Ba lô"],
        "key_phrases": ["Anh sẵn sàng chưa?", "Sáng mai", "thỏa thuận ngầm không lời"]
    },
    {
        "text": "Không cần những lời giải thích thừa thãi, không cần những cam kết rườm rà. Trong bầu không khí ngột ngạt của Omega-7, sự im lặng mang nhiều trọng lượng hơn bất kỳ từ ngữ nào. ",
        "beat_action": "Standing in silence under the haze",
        "description": "{RÌA ZONE 4}, medium close-up, eye-level, {Tiểu Kỳ} sits on the metal guardrail, her face pale and expressionless, while {Hùng} stands nearby in the background. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Medium close-up, eye-level shot. Lens: 85mm lens, shallow depth of field with soft bokeh of the hazy background. Lighting: low contrast, soft grey and orange tones of dawn. Composition: {Tiểu Kỳ} is the primary subject on the left side of the frame, showing her profile looking east, while {Hùng}'s shoulder and kaki coat are visible on the right. Mood: melancholic, silent, heavy atmospheric haze.",
        "motion_prompt": "Camera movement: slow crane down. Atmosphere: fine grey dust particles drifting slowly across the frame. Subject motion: {Tiểu Kỳ} blinks slowly, maintaining her gaze east.",
        "ref_entity_names": ["RÌA ZONE 4", "Tiểu Kỳ", "Hùng"],
        "key_phrases": ["không cần những cam kết", "sự im lặng mang nhiều trọng lượng"]
    },
    {
        "text": "Họ gặp nhau tại điểm đầu của con đường kỹ thuật chạy dọc rìa Zone 4. ",
        "beat_action": "Meeting at the technical road",
        "description": "{RÌA ZONE 4}, wide shot, low angle, the two characters stand together on the deserted technical road at {RÌA ZONE 4}. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Wide shot, low angle. Lens: 28mm wide lens, deep focus. Lighting: cold early morning light with a pale orange sky on the horizon. Composition: the road runs diagonally across the frame, leading lines pointing towards the background. {Hùng} stands on the road next to {Tiểu Kỳ} who is sitting on the rusty guardrail with her canvas {Ba lô} near her. Mood: solitary, cold, industrial edge.",
        "motion_prompt": "Camera movement: locked-off, no camera move. Light: cold morning shadows fading slightly. Subject motion: a gust of wind blows a few grey particles along the road.",
        "ref_entity_names": ["RÌA ZONE 4", "Hùng", "Tiểu Kỳ", "Ba lô"],
        "key_phrases": ["con đường kỹ thuật chạy dọc rìa Zone 4"]
    },
    {
        "text": "Đây chính là nơi hai tuần trước, Trần Thiên Ân đã đứng lặng lẽ trong bóng tối ẩm ướt của đêm muộn, dán mắt vào cánh cổng thép của trạm DN-31 để tìm kiếm một dấu vết vô hình. ",
        "beat_action": "Recalling past event",
        "description": "{RÌA ZONE 4}, extreme wide shot, eye-level, the empty technical road at {RÌA ZONE 4} extending into the distance under the morning fog. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Extreme wide shot, eye-level. Lens: 24mm wide lens, deep focus. Lighting: misty morning light, highly diffused and cold, with orange glow from the sun filtered through thick pollution. Composition: the vast industrial landscape of {RÌA ZONE 4}, with the tiny figures of {Hùng} and {Tiểu Kỳ} on the guardrail on one side, and the massive dark steel pipes and structures on the other. Mood: eerie, nostalgic, desolate.",
        "motion_prompt": "Camera movement: slow push-in along the road. Atmosphere: morning fog drifting slowly across the structures. Subject motion: the characters remain still in the distance.",
        "ref_entity_names": ["RÌA ZONE 4", "Hùng", "Tiểu Kỳ"],
        "key_phrases": ["đứng lặng lẽ trong bóng tối", "tìm kiếm một dấu vết"]
    },
    {
        "text": "Hùng đến điểm hẹn lúc sáu giờ mười hai phút sáng. Tiểu Kỳ đã ở đó từ trước. ",
        "beat_action": "Hùng arriving at the meeting place",
        "description": "{RÌA ZONE 4}, medium shot, high angle, {Hùng} walking towards the guardrail where {Tiểu Kỳ} is already waiting. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Medium shot, high angle. Lens: 35mm lens, deep focus. Lighting: soft golden light from the rising sun behind {Tiểu Kỳ}, creating a rim light on her silhouette. Composition: {Hùng} entering the frame from the left, wearing his kaki coat, walking towards {Tiểu Kỳ} who is sitting calmly on the guardrail on the right with her worn canvas {Ba lô} at her feet. Mood: anticipation, quiet encounter.",
        "motion_prompt": "Camera movement: slow pan following {Hùng}'s movement. Subject motion: {Hùng} steps forward on the gravel road and stops near the guardrail.",
        "ref_entity_names": ["RÌA ZONE 4", "Hùng", "Tiểu Kỳ", "Ba lô"],
        "key_phrases": ["đến điểm hẹn lúc sáu giờ", "ở đó từ trước"]
    },
    {
        "text": "Cô ngồi lặng lẽ trên thanh chắn kim loại gỉ sét đã bong tróc hết lớp sơn bảo ôn, chiếc ba lô vải dù sờn rách đặt ngay dưới chân. ",
        "beat_action": "Staring at Tiểu Kỳ on the guardrail",
        "description": "{RÌA ZONE 4}, full shot, eye-level, {Tiểu Kỳ} sitting on the peeling guardrail, her canvas {Ba lô} resting at her boots. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Full shot, eye-level. Lens: 50mm portrait lens, shallow depth of field. Lighting: soft natural morning daylight highlighting the texture of the rusty guardrail and the worn canvas of the {Ba lô}. Composition: {Tiểu Kỳ} centered, sitting on the rusty guardrail with her boots resting on the ground, the torn canvas {Ba lô} sitting at her feet. {Hùng} is partially visible standing in the background. Mood: silent, weathered, realistic sci-fi detail.",
        "motion_prompt": "Camera movement: locked-off, no camera move. Atmosphere: tiny dust particles glinting in the soft sunlight. Subject motion: {Tiểu Kỳ} sits quietly, her hands resting in her lap.",
        "ref_entity_names": ["RÌA ZONE 4", "Tiểu Kỳ", "Ba lô", "Hùng"],
        "key_phrases": ["thanh chắn kim loại gỉ sét", "ba lô vải dù sờn rách"]
    },
    {
        "text": "Đôi mắt cô hướng về phía đông, nơi đường chân trời đang chuyển dần từ màu xám đục sang một vệt cam nhạt nhòa thiếu sức sống — cái thứ ánh sáng rỉ ra từ bộ lọc khí công nghiệp của thành phố trong một buổi sớm tháng chín. ",
        "beat_action": "Looking at the sunrise",
        "description": "{RÌA ZONE 4}, extreme wide shot, high angle, looking from behind the characters towards the hazy orange horizon. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Extreme wide shot, high angle from behind. Lens: 24mm wide lens, deep focus. Lighting: pale orange glow rising on the eastern horizon, filtering through thick industrial smog and grey haze. Composition: silhouette of {Tiểu Kỳ} on the guardrail and {Hùng} standing next to her in the foreground, looking out over a vast industrial valley with smoke stacks. Mood: cinematic, quiet awe, industrial pollution, melancholic beauty.",
        "motion_prompt": "Camera movement: slow tilt up towards the sky. Atmosphere: dense smog drifting across the industrial skyline. Subject motion: both characters remain motionless, staring at the sunrise.",
        "ref_entity_names": ["RÌA ZONE 4", "Tiểu Kỳ", "Hùng"],
        "key_phrases": ["đường chân trời", "cam nhạt nhòa thiếu sức sống", "bộ lọc khí công nghiệp"]
    },
    {
        "text": "“Anh mang theo những gì?” cô hỏi, giọng nói phẳng lặng, không hề quay đầu lại. ",
        "beat_action": "Tiểu Kỳ asking Hùng",
        "description": "{RÌA ZONE 4}, medium shot, over-the-shoulder, looking over {Hùng}'s shoulder at {Tiểu Kỳ} sitting on the guardrail. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Medium shot, over-the-shoulder angle. Lens: 50mm lens, shallow depth of field. Lighting: side lighting from the morning sun, casting a soft glow on {Tiểu Kỳ}'s pale face. Composition: {Hùng}'s kaki coat shoulder in the foreground on the left, framing {Tiểu Kỳ} on the right as she sits looking away towards the east. Her canvas {Ba lô} is at the bottom of the frame. Mood: quiet, focused dialogue.",
        "motion_prompt": "Camera movement: slow push-in on {Tiểu Kỳ}. Subject motion: {Tiểu Kỳ} speaks calmly without turning her head, her lips moving.",
        "ref_entity_names": ["RÌA ZONE 4", "Hùng", "Tiểu Kỳ", "Ba lô"],
        "key_phrases": ["Anh mang theo những gì?", "giọng nói phẳng lặng"]
    },
    {
        "text": "“Sổ tay giấy. Đèn pin LED. Thiết bị đo tần số cầm tay ngoại tuyến,” Hùng dừng lại một nhịp ngắn, bàn tay vỗ nhẹ vào túi áo khoác kaki dày. “Và nước uống.” ",
        "beat_action": "Hùng listing his gear",
        "description": "{RÌA ZONE 4}, medium close-up, eye-level, {Hùng} listing his gear, patting the pocket of his thick kaki coat. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Medium close-up, eye-level shot. Lens: 50mm portrait lens, shallow depth of field. Lighting: soft golden sunlight on {Hùng}'s face and glasses. Composition: {Hùng} in the center, his hands patting his kaki coat pocket where the outlines of his paper {Sổ tay}, a handheld {Thiết bị đo tần số}, and a LED {Đèn pin} are visible. {Tiểu Kỳ} is visible in soft focus in the background. Mood: methodical, serious, prepared.",
        "motion_prompt": "Camera movement: static lock-off, no camera move. Subject motion: {Hùng} speaks, his hand patting his coat pocket, feeling the tools inside.",
        "ref_entity_names": ["RÌA ZONE 4", "Hùng", "Sổ tay", "Đèn pin", "Thiết bị đo tần số", "Tiểu Kỳ"],
        "key_phrases": ["Sổ tay giấy", "Thiết bị đo tần số", "vỗ nhẹ vào túi áo"]
    },
    {
        "text": "“Tốt.” Cô đứng dậy, cúi xuống xách chiếc ba lô lên vai. “Đừng ghi chép bất kỳ điều gì vào thiết bị điện tử khi chúng ta ở bên dưới. Chỉ dùng sổ giấy và bút chì.” ",
        "beat_action": "Tiểu Kỳ lifting her backpack",
        "description": "{RÌA ZONE 4}, medium shot, over-the-shoulder, looking over {Tiểu Kỳ}'s shoulder as she stands up and lifts her worn {Ba lô}. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Medium shot, over-the-shoulder angle. Lens: 35mm lens, deep focus. Lighting: early morning sun behind {Tiểu Kỳ}, casting her shadow towards {Hùng}. Composition: {Tiểu Kỳ} in the foreground on the right, standing up from the rusty guardrail and putting the strap of her canvas {Ba lô} on her shoulder, looking at {Hùng} who stands on the left. Mood: instruction, preparation, dark adventure.",
        "motion_prompt": "Camera movement: slow tilt up as {Tiểu Kỳ} stands up. Subject motion: {Tiểu Kỳ} bends down, picks up the canvas {Ba lô}, and swings it onto her shoulder.",
        "ref_entity_names": ["RÌA ZONE 4", "Tiểu Kỳ", "Ba lô", "Hùng"],
        "key_phrases": ["Cô đứng dậy", "Chỉ dùng sổ giấy và bút chì"]
    },
    {
        "text": "Hùng nhíu mày dưới gọng kính kim loại mỏng. “Tại sao?” ",
        "beat_action": "Hùng questioning her instruction",
        "description": "{RÌA ZONE 4}, close-up, low angle, {Hùng} frowning slightly behind his thin metal glasses, looking down at {Tiểu Kỳ}. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Close-up, low angle shot. Lens: 85mm portrait lens, shallow depth of field. Lighting: direct early morning sun glinting off the metal frame of {Hùng}'s glasses, casting sharp shadows on his face. Composition: tight shot of {Hùng}'s face, showing his frown and glasses, with his kaki coat collar visible. In the background, the soft outline of {Tiểu Kỳ} standing. Mood: analytical, skeptical, curious.",
        "motion_prompt": "Camera movement: slow push-in. Focus: sharp on his eyes and glasses. Subject motion: {Hùng}'s brow furrows as he speaks the question.",
        "ref_entity_names": ["RÌA ZONE 4", "Hùng", "Tiểu Kỳ"],
        "key_phrases": ["nhíu mày dưới gọng kính", "Tại sao?"]
    },
    {
        "text": "“Có một thứ trường lực đặc biệt trong đó. Nó không phá hủy phần cứng, nhưng nó sẽ làm nhiễu loạn các ô nhớ. ",
        "beat_action": "Tiểu Kỳ explaining the field",
        "description": "{RÌA ZONE 4}, medium shot, over-the-shoulder, looking over {Hùng}'s shoulder at {Tiểu Kỳ} as she explains the phenomenon. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Medium shot, over-the-shoulder angle. Lens: 50mm lens, shallow depth of field. Lighting: soft warm light on {Tiểu Kỳ}'s face, cool shadow side. Composition: {Hùng}'s shoulder on the left, {Tiểu Kỳ} standing on the right, her eyes fixed on him as she speaks. The canvas {Ba lô} is visible on her shoulder. Background: the hazy sky of {RÌA ZONE 4}. Mood: serious, informative, sci-fi anomaly.",
        "motion_prompt": "Camera movement: static lock-off, no camera move. Subject motion: {Tiểu Kỳ} speaks calmly, her expression grave and steady.",
        "ref_entity_names": ["RÌA ZONE 4", "Tiểu Kỳ", "Ba lô", "Hùng"],
        "key_phrases": ["trường lực đặc biệt", "làm nhiễu loạn các ô nhớ"]
    },
    {
        "text": "Mọi dữ liệu số anh lưu lại bên dưới sẽ tự động biến mất hoặc biến dạng thành các chuỗi ký tự rác ngay khi anh bước trở lại mặt đất.” ",
        "beat_action": "Continuing the explanation",
        "description": "{RÌA ZONE 4}, medium close-up, dutch tilt, {Tiểu Kỳ} explaining the data corruption effect. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Medium close-up, dutch tilt angle. Lens: 50mm lens, shallow depth of field. Lighting: warm key light from the side, cool grey fills, high contrast. Composition: canted angle creating a sense of disorientation, focusing on {Tiểu Kỳ}'s expression. In the soft-focus background, {Hùng} is visible listening. Mood: tense, warnings, technological dread.",
        "motion_prompt": "Camera movement: slow dolly-in. Light: soft dust particles drifting around the characters. Subject motion: {Tiểu Kỳ} speaks, her eyes serious, emphasizing her warning.",
        "ref_entity_names": ["RÌA ZONE 4", "Tiểu Kỳ", "Hùng"],
        "key_phrases": ["dữ liệu số", "biến dạng thành các chuỗi ký tự rác"]
    },
    {
        "text": "Cô chỉnh lại quai đeo ba lô, ánh mắt lạnh lùng quét qua chiếc điện thoại đang tắt nguồn trong túi anh. “Tôi đã thử. Nhiều lần. Không có ngoại lệ.” ",
        "beat_action": "Tiểu Kỳ adjusting her backpack strap",
        "description": "{RÌA ZONE 4}, close-up, high angle, {Tiểu Kỳ}'s hand adjusting the strap of her worn canvas {Ba lô}, with her cold gaze directed towards {Hùng}'s coat pocket. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Close-up, high angle. Lens: 85mm portrait lens, shallow depth of field. Lighting: soft morning sun casting long shadows, highlighting the textured fabric of the {Ba lô} strap. Composition: tight shot of {Tiểu Kỳ}'s pale hand on her backpack strap in the foreground, with {Hùng}'s kaki coat pocket where his phone would be located visible in the background. Mood: cold, resolute, experienced.",
        "motion_prompt": "Camera movement: static lock-off, no camera move. Subject motion: {Tiểu Kỳ}'s fingers adjust the strap, her movement slow and deliberate.",
        "ref_entity_names": ["RÌA ZONE 4", "Tiểu Kỳ", "Ba lô", "Hùng"],
        "key_phrases": ["chỉnh lại quai đeo ba lô", "Không có ngoại lệ"]
    },
    {
        "text": "Hùng nhìn cô chăm chú. Gương mặt cô vẫn giữ nguyên vẻ nhợt nhạt đặc trưng của những người sống dưới tầng tối, nhưng trong đôi mắt đen sâu thẳm kia không có chỗ cho sự mơ hồ. “Cô đã thử bằng thiết bị gì?”",
        "beat_action": "Hùng asking about her experiments",
        "description": "{RÌA ZONE 4}, extreme close-up, eye-level, {Tiểu Kỳ}'s deep black eyes, reflecting the dim orange sunrise, while {Hùng} stares intently. Comic style, sci-fi theme.",
        "visual_prompt": "Comic style, sci-fi theme. Extreme close-up, eye-level shot. Lens: 135mm macro lens, razor-thin depth of field. Lighting: soft orange highlight on the iris of {Tiểu Kỳ}'s deep black eyes, contrasting with her pale skin. Composition: framing tightly on {Tiểu Kỳ}'s eyes, showing their depth and clarity, with {Hùng}'s reflection faint in her pupil. Mood: intense, investigative, psychological connection.",
        "motion_prompt": "Camera movement: slow push-in. Subject motion: {Tiểu Kỳ}'s eyes remain locked, blinking once slowly as {Hùng}'s voice asks the question.",
        "ref_entity_names": ["RÌA ZONE 4", "Tiểu Kỳ", "Hùng"],
        "key_phrases": ["nhìn cô chăm chú", "đôi mắt đen sâu thẳm", "thử bằng thiết bị gì"]
    }
]

# Ensure it's valid JSON
print(json.dumps(beats, ensure_ascii=False, indent=2))
