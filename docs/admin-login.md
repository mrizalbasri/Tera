# Autentikasi dan Akses Klaim (Native JWT)

## Status Autentikasi

Tera menggunakan autentikasi **Native JWT** (HMAC-SHA256) mandiri, tanpa layanan pihak ketiga seperti Clerk.

Sesi pengguna dikelola menggunakan cookie HTTP-only `__session` dan header `Authorization: Bearer <token>`.

### Fitur Kunci:
1. **Endpoint Auth**:
   - `POST /auth/login`: Menerima `username` dan `password`. Memvalidasi kredensial pengguna, menerbitkan JWT bertanda tangan HS256, dan menetapkan cookie `__session` (HTTP-only, SameSite=Lax).
   - `POST /auth/logout`: Menghapus cookie `__session`.
   - `GET /auth/session`: Mengembalikan identitas pengguna dan role (`admin` atau `member`).

2. **Otorisasi Role**:
   - Role pengguna ditentukan dari daftar `ADMIN_USERS` di konfigurasi backend.
   - Pengecekan admin dilakukan secara tepat (exact match) terhadap daftar nama pengguna admin.
   - Karyawan biasa diarahkan ke `/pengajuan` atau `/riwayat`.
   - Admin diarahkan ke `/reviews` dan memiliki akses ke `/reports`, `/policies`, dan `/operations`.

3. **Mode Demo Opsional**:
   - Ketika `DEMO_MODE=true`, autentikasi disederhanakan untuk keperluan demonstrasi lokal.
   - Identitas pengulas diset sebagai `demo-reviewer`.
   - Mode demo dilarang di production (`ENVIRONMENT=production`).

## Konfigurasi Environment

Backend `.env`:
```dotenv
SECRET_KEY=kunci-rahasia-minimal-32-karakter-harus-diubah-di-production
ADMIN_USERS=admin,reviewer,finance
FRONTEND_ORIGIN=http://localhost:5173
```

Frontend `.env`:
```dotenv
BACKEND_URL=http://127.0.0.1:8000
```

## Keamanan

- **Password Verification**: Setiap permintaan login memvalidasi password.
- **Role Assignment**: Client tidak dapat menetapkan role sendiri; role selalu dievaluasi oleh backend.
- **Prefix Matching Dimatikan**: Username yang diawali nama prefix (seperti `admin_fake`) tidak otomatis menjadi admin.
- **Cookie Security**: Cookie `__session` berflag `HttpOnly` dan `Secure` (di production).
