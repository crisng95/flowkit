# FlowKit License Activation (Cloudflare)

Tài liệu này hướng dẫn triển khai hệ thống license theo máy cho FlowKit:

- `cloudflare-license/`: Worker API + CMS quản trị license
- `desktop/`: App Electron có license gate ngay khi mở app

## 1) Kiến trúc

1. App desktop sinh `Machine ID` ổn định theo máy.
2. App gọi `POST /v1/device/check` trên Worker để xác minh license.
3. Admin vào CMS (`/admin`) để active/revoke theo `Machine ID`.
4. Chỉ máy `ACTIVE` mới vào được UI chính.

## 2) Triển khai Worker + CMS lên Cloudflare

### Bước 0: Chọn account Cloudflare (bắt buộc nếu có nhiều account)

Nếu `wrangler` báo lỗi nhiều account, set `account_id` trong `cloudflare-license/wrangler.toml`:

```toml
account_id = "<YOUR_CLOUDFLARE_ACCOUNT_ID>"
```

Hoặc export env khi chạy lệnh:

```bash
export CLOUDFLARE_ACCOUNT_ID=<YOUR_CLOUDFLARE_ACCOUNT_ID>
```

### Bước 1: Cài dependencies

```bash
cd cloudflare-license
npm install
```

### Bước 2: Tạo D1 database

```bash
npx wrangler d1 create flowkit_license
```

Copy `database_id` trả về và cập nhật vào `cloudflare-license/wrangler.toml`:

```toml
[[d1_databases]]
binding = "LICENSE_DB"
database_name = "flowkit_license"
database_id = "<YOUR_DATABASE_ID>"
```

### Bước 3: Chạy migration schema

```bash
npx wrangler d1 migrations apply flowkit_license --remote
```

### Bước 4: Set thông tin đăng nhập CMS (bắt buộc)

```bash
npx wrangler secret put ADMIN_USERNAME
npx wrangler secret put ADMIN_PASSWORD
npx wrangler secret put SESSION_SECRET
```

`SESSION_SECRET` nên là chuỗi ngẫu nhiên dài (ví dụ 32-64 ký tự hex/base64).

`ADMIN_TOKEN` chỉ dùng fallback khi chưa bật login username/password. Khi đã cấu hình login, admin API bắt buộc session đăng nhập.

### Bước 5: (Tuỳ chọn) giới hạn CORS origin

Mặc định đang là `*`. Có thể sửa `vars.CORS_ORIGIN` trong `wrangler.toml`:

```toml
[vars]
CORS_ORIGIN = "https://app.example.com"
```

### Bước 6: Deploy

```bash
npx wrangler deploy
```

Sau deploy sẽ có URL dạng:

- `https://flowkit-license.<subdomain>.workers.dev`

CMS nằm tại:

- `https://flowkit-license.<subdomain>.workers.dev/admin`

CMS đã tách giao diện theo flow:

- `Login form` (username/password)
- đăng nhập thành công mới vào `Dashboard`
- Dashboard hiển thị đầy đủ `Machine ID` + trạng thái `REVOKED` + reason.

## 3) Cấu hình app desktop

Khi mở app lần đầu, màn hình license gate hiển thị:

- `Machine ID` (copy gửi cho admin)
- `License API URL` (paste URL Worker)

Ví dụ:

```text
https://flowkit-license.<subdomain>.workers.dev
```

App sẽ lưu URL vào:

- `~/Library/Application Support/FlowKit/license-config.json` (macOS)

và cache license active tại:

- `~/Library/Application Support/FlowKit/license-cache.json`

## 4) Quy trình active license theo máy

1. User mở app, copy `Machine ID`.
2. Admin đăng nhập CMS `/admin` bằng username/password.
3. Nhập `Machine ID`, chọn gói:
   - `1M`, `3M`, `6M`, `1Y`, `LIFE`
4. Bấm `Active License`.
5. User quay lại app, bấm `Kiểm tra lại license`.
6. Khi trạng thái `Đã kích hoạt`, app mở toàn bộ chức năng.

## 5) API chính

- `POST /v1/device/check`: app kiểm tra quyền dùng
- `GET /v1/admin/devices`: danh sách máy
- `GET /v1/admin/licenses`: lịch sử license
- `POST /v1/admin/licenses/activate`: active máy
- `POST /v1/admin/licenses/revoke`: thu hồi license

## 6) Bảo mật khuyến nghị trước thương mại hoá

1. Không dùng `CORS_ORIGIN = "*"` khi production.
2. Rotate định kỳ: `ADMIN_PASSWORD`, `SESSION_SECRET`, `ADMIN_TOKEN`.
3. Đặt Cloudflare Access/IP policy cho `/admin` nếu cần.
4. Bật log/audit review thường xuyên (`audit_logs` trong D1).
5. Cân nhắc hash password (Argon2/Bcrypt) ở phase tiếp theo.

## 7) Kiểm tra nhanh local

```bash
cd cloudflare-license
npx wrangler d1 migrations apply flowkit_license --local
npx wrangler dev
```

Mở:

- `http://127.0.0.1:8787/admin`

và cấu hình app trỏ vào `http://127.0.0.1:8787`.
