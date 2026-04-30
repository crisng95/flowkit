import Modal from '../ui/Modal'

interface Props {
    guide: 'camera' | 'thumbnail'
    onClose: () => void
}

const CAMERA_GUIDE = {
    title: 'Camera Guide (fk:camera-guide)',
    sections: [
        {
            heading: 'Prompt Structure',
            points: [
                'Giữ prompt 100-150 từ, dạng prose tự nhiên.',
                'Câu camera movement tách riêng khỏi câu action.',
                'Kết prompt bằng Audio/SFX/Music + Negative: subtitles, watermark, text overlay.',
                'Với project dùng reference image, scene prompt tập trung ACTION + SETTING, không mô tả lại ngoại hình nhân vật.',
            ],
        },
        {
            heading: 'Shot & Movement',
            points: [
                'Shot: EWS, WS, MS, CU, ECU, Macro.',
                'Movement: dolly in/out, pan, tilt, tracking, crane, handheld, whip pan, arc, POV, static.',
                'Mỗi shot nên có 1 movement chính để model bám sát.',
            ],
        },
        {
            heading: 'Lighting & Style',
            points: [
                'Luôn chỉ định lighting: golden hour, low-key, backlight, volumetric, noir…',
                'Giữ style nhất quán theo sequence (color grade, lens, tone).',
                'Multi-shot 8s: tối ưu 2-3 góc, tránh nhồi quá nhiều cut.',
            ],
        },
        {
            heading: 'Audio Labels',
            points: [
                'Audio: ambient liên tục (mưa, gió, phố).',
                'SFX: âm thanh sự kiện (footsteps, door slam, gun cock).',
                'Dialogue ngắn, tối đa 10-15 từ/nhân vật/2-3s segment.',
            ],
        },
    ],
}

const THUMBNAIL_GUIDE = {
    title: 'Thumbnail Guide (fk:thumbnail-guide)',
    sections: [
        {
            heading: 'Core Rules',
            points: [
                'Text 0-3 từ, chữ dày, đặt ở nửa trên ảnh.',
                'Gương mặt/subject chiếm 30-60% frame, cảm xúc mạnh.',
                'Màu tương phản cao, tránh palette nhạt xám.',
                'Một focal point rõ ràng, background đơn giản.',
            ],
        },
        {
            heading: '6 Formula Gợi Ý',
            points: [
                'Reaction Face',
                'Before/After Split',
                'Contrast/Clash (small vs massive)',
                'Mystery/Reveal',
                'High Stakes Frame',
                'Number Punch',
            ],
        },
        {
            heading: 'Technical',
            points: [
                'Kích thước chuẩn YouTube: 1280x720 (16:9).',
                'Safe zone: vùng trung tâm 90%.',
                'Tránh góc phải dưới vì YouTube đặt duration badge.',
                'Luôn test readability ở kích thước mobile.',
            ],
        },
    ],
}

export default function GuideModal({ guide, onClose }: Props) {
    const content = guide === 'camera' ? CAMERA_GUIDE : THUMBNAIL_GUIDE

    return (
        <Modal title={content.title} onClose={onClose} width={700}>
            <div className="flex flex-col gap-4">
                {content.sections.map(section => (
                    <div key={section.heading} className="rounded p-3" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                        <div className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--muted)' }}>
                            {section.heading}
                        </div>
                        <div className="flex flex-col gap-1.5">
                            {section.points.map(point => (
                                <div key={point} className="text-xs" style={{ color: 'var(--text)' }}>• {point}</div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </Modal>
    )
}
