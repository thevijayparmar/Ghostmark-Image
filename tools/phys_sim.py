"""Simulated photo of a screen or a printed copy (test helper)."""
import numpy as np, cv2, math

CAMW, CAMH = 3024, 2268


def rot(yaw, pitch, roll):
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Rz @ Rx @ Ry


def project_rect(w, h, yaw, pitch, roll, fill, cx=0.5, cy=0.5):
    """Corners (TL,TR,BR,BL) of a w x h plane seen at given angles so it fills ~fill of camera height."""
    pts = np.array([[-w / 2, -h / 2, 0], [w / 2, -h / 2, 0], [w / 2, h / 2, 0], [-w / 2, h / 2, 0]], float)
    R = rot(math.radians(yaw), math.radians(pitch), math.radians(roll))
    f = 1.1 * CAMW
    pr = pts @ R.T
    # distance so the projected height ~ fill*CAMH
    z = f * h / (fill * CAMH)
    pr[:, 2] += z
    uv = np.stack([f * pr[:, 0] / pr[:, 2] + CAMW * cx, f * pr[:, 1] / pr[:, 2] + CAMH * cy], 1)
    return uv.astype(np.float32)


def simulate(photo_bgr, kind, yaw, pitch, roll, blur, noise, jpegq, seed=0, fill=0.86):
    rng = np.random.default_rng(seed)
    ph, pw = photo_bgr.shape[:2]
    if kind == 'monitor':
        SW, SH = 1920, 1080
        sc = min(SW / pw, SH / ph)
        w, h = int(pw * sc), int(ph * sc)
        scr = np.zeros((SH, SW, 3), np.uint8)
        scr[:] = (4, 4, 4)
        x0, y0 = (SW - w) // 2, (SH - h) // 2
        scr[y0:y0 + h, x0:x0 + w] = cv2.resize(photo_bgr, (w, h), interpolation=cv2.INTER_AREA)
        flat = scr.astype(np.float32)
        yy, xx = np.mgrid[0:SH, 0:SW]
        # pixel-grid / moire beat pattern
        flat *= (1 + 0.025 * np.sin(2 * np.pi * (xx / 3.0))[..., None]) * (1 + 0.02 * np.sin(2 * np.pi * (xx * 0.6 + yy * 0.8) / 41.0)[..., None])
        src = np.clip(flat, 0, 255)
        corners_src = np.array([[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h]], np.float32)
        surround = (3, 3, 4)
        quad = project_rect(SW, SH, yaw, pitch, roll, fill=fill * min(1.0, 0.99))
        # shrink so that the screen plane fits horizontally
        Wp, Hp = SW, SH
    else:  # print
        PW, PH = 1700, 1250
        paper = np.full((PH, PW, 3), (236, 240, 244), np.float32)
        sc = min((PW * 0.90) / pw, (PH * 0.90) / ph)
        w, h = int(pw * sc), int(ph * sc)
        x0, y0 = (PW - w) // 2, (PH - h) // 2
        im = cv2.resize(photo_bgr, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)
        g = im.mean(2, keepdims=True)
        im = g + (im - g) * 0.68                      # copier desaturation
        im = 18 + (im / 255.0) ** 1.12 * 205         # lifted blacks, dull whites
        im[..., 2] *= 1.05
        im[..., 0] *= 0.93                           # warm cast
        yy, xx = np.mgrid[0:h, 0:w]
        half = np.sin(2 * np.pi * (xx + yy) / (5.0 * math.sqrt(2))) * np.sin(2 * np.pi * (xx - yy) / (5.0 * math.sqrt(2)))
        im *= (1 + 0.05 * half)[..., None]
        paper[y0:y0 + h, x0:x0 + w] = im
        paper += rng.normal(0, 2.0, paper.shape)
        src = np.clip(paper, 0, 255)
        SW, SH = PW, PH
        corners_src = np.array([[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h]], np.float32)
        surround = (45, 62, 80)
        quad = project_rect(PW, PH, yaw, pitch, roll, fill=fill)
    Hm = cv2.getPerspectiveTransform(np.array([[0, 0], [SW, 0], [SW, SH], [0, SH]], np.float32), quad)
    cam = np.empty((CAMH, CAMW, 3), np.uint8)
    cam[:] = surround
    warped = cv2.warpPerspective(src.astype(np.uint8), Hm, (CAMW, CAMH), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=surround)
    cam = warped.astype(np.float32)
    true_corners = cv2.perspectiveTransform(corners_src.reshape(1, 4, 2), Hm).reshape(4, 2)
    # camera optics
    if blur > 0:
        cam = cv2.GaussianBlur(cam, (0, 0), blur)
    yy, xx = np.mgrid[0:CAMH, 0:CAMW]
    vig = 1 - 0.18 * (((xx - CAMW / 2) / CAMW) ** 2 + ((yy - CAMH / 2) / CAMH) ** 2) * 4
    cam *= vig[..., None]
    cam = 255 * (np.clip(cam / 255, 0, 1) ** 1.08)
    cam[..., 2] *= 1.04
    cam[..., 0] *= 0.96
    cam += rng.normal(0, noise, cam.shape)
    cam = np.clip(cam, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode('.jpg', cam, [cv2.IMWRITE_JPEG_QUALITY, jpegq])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR), true_corners.astype(np.float32)


