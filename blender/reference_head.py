"""Procedural heads inspired by the two supplied portrait motifs.

The heads use a continuous sculpted ring surface rather than stacked primitives.
They are deliberately original interpretations: no photographic textures, names,
uniform insignia, or personal identity information are embedded in the assets.
Coordinates are metres, Z-up, with the face looking along -Y.
"""
import math
import random


HEAD = 'HEAD_CTRL'
NECK = 'NECK_CTRL'
TAU = math.tau


def _get(profile, key, default=None):
    return profile.get(key, default) if isinstance(profile, dict) else getattr(profile, key, default)


def _lerp_table(z, table):
    if z <= table[0][0]:
        return table[0][1]
    slopes = [(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(table, table[1:])]
    tangents = [slopes[0]]
    for i in range(1, len(table) - 1):
        left, right = slopes[i - 1], slopes[i]
        if left * right <= 0:
            tangents.append(0.0)
        else:
            da = table[i][0] - table[i - 1][0]
            db = table[i + 1][0] - table[i][0]
            wa, wb = 2 * db + da, db + 2 * da
            tangents.append((wa + wb) / (wa / left + wb / right))
    tangents.append(slopes[-1])
    for i, ((a, va), (b, vb)) in enumerate(zip(table, table[1:])):
        if z <= b:
            t = (z - a) / (b - a)
            # Monotone Hermite interpolation keeps the derivative continuous.
            # Independent ease-in/out at every row made cheeks look banded.
            return ((2 * t ** 3 - 3 * t ** 2 + 1) * va
                    + (t ** 3 - 2 * t ** 2 + t) * (b - a) * tangents[i]
                    + (-2 * t ** 3 + 3 * t ** 2) * vb
                    + (t ** 3 - t ** 2) * (b - a) * tangents[i + 1])
    return table[-1][1]


def _gaussian(x, z, cx, cz, wx, wz):
    return math.exp(-((x - cx) / wx) ** 2 - ((z - cz) / wz) ** 2)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    length = max(1e-9, math.sqrt(sum(v * v for v in a)))
    return tuple(v / length for v in a)


def _tube_append(verts, faces, uvs, points, radii, sides=6):
    """Add a strand to one shared mesh, keeping object/material counts small."""
    start = len(verts)
    for j, point in enumerate(points):
        prev, nxt = points[max(j - 1, 0)], points[min(j + 1, len(points) - 1)]
        tangent = _unit(tuple(nxt[k] - prev[k] for k in range(3)))
        right = _unit(_cross(tangent, (0, 1, 0) if abs(tangent[1]) < .9 else (1, 0, 0)))
        up = _unit(_cross(tangent, right))
        radius = radii[j]
        for i in range(sides):
            a = TAU * i / sides
            verts.append(tuple(point[k] + radius * (right[k] * math.cos(a) + up[k] * math.sin(a)) for k in range(3)))
            uvs.append((i / sides, j / max(1, len(points) - 1)))
    for j in range(len(points) - 1):
        for i in range(sides):
            a, b = start + j * sides + i, start + j * sides + (i + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(start + i for i in reversed(range(sides))))
    faces.append(tuple(start + (len(points) - 1) * sides + i for i in range(sides)))


def _ribbon_append(verts, faces, uvs, points, widths, ridge=.00065):
    """A flat tapered hair lock with one tiny raised centre, never a round pipe."""
    start = len(verts)
    normals = []
    for j, point in enumerate(points):
        prev, nxt = points[max(j - 1, 0)], points[min(j + 1, len(points) - 1)]
        tangent = _unit(tuple(nxt[k] - prev[k] for k in range(3)))
        normal = _unit((point[0], point[1] - .010, (point[2] - 1.803) * .80))
        right = _unit(_cross(normal, tangent))
        normals.append(normal)
        for i, across in enumerate((-1, 0, 1)):
            lift = ridge if across == 0 else 0
            verts.append(tuple(point[k] + widths[j] * across * right[k] + lift * normal[k] for k in range(3)))
            uvs.append((i / 2, j / max(1, len(points) - 1)))
    for j in range(len(points) - 1):
        for i in range(2):
            a = start + j * 3 + i
            face = (a, a + 1, a + 4, a + 3)
            ab = tuple(verts[a + 1][k] - verts[a][k] for k in range(3))
            ac = tuple(verts[a + 3][k] - verts[a][k] for k in range(3))
            facing = sum(x * y for x, y in zip(_cross(ab, ac), normals[j]))
            faces.append(face if facing >= 0 else tuple(reversed(face)))


def build_head(api, profile):
    """Build one rigged head using the generator's mesh/curve/tube helpers.

    ``profile.id`` is ``glasses`` or ``cropped``. Optional ``head_scale`` scales
    X/Y dimensions while preserving the agreed neck and face height landmarks.
    The body generator can join these objects and bake its own shared atlas.
    """
    glasses = _get(profile, 'id') == 'glasses'
    prefix = 'Archivist' if glasses else 'Warden'
    scale = float(_get(profile, 'head_scale', 1.0))
    eye_x = (.0435 if glasses else .048) * scale
    eye_z = 1.813 if glasses else 1.807
    mouth_z = 1.714 if glasses else 1.709

    # Profiles preserve a longer, narrower chin for the glasses character and
    # a broad mandibular angle/full cheek for the cropped-hair character.
    width = [(1.625, .027), (1.637, .051 if glasses else .060),
             (1.66, .077 if glasses else .089), (1.695, .098 if glasses else .112),
             (1.738, .110 if glasses else .125), (1.778, .119 if glasses else .130),
             (1.819, .115 if glasses else .126), (1.862, .115 if glasses else .123),
             (1.898, .107 if glasses else .114), (1.93, .082 if glasses else .087),
             (1.95, .045), (1.959, .004)]
    front = [(1.625, .064), (1.646, .099), (1.687, .109),
             (1.723, .125 if glasses else .134), (1.768, .130 if glasses else .139),
             (1.815, .127 if glasses else .137), (1.851, .128),
             (1.89, .120), (1.93, .087), (1.959, .013)]
    back = [(1.625, .061), (1.68, .085), (1.75, .112),
            (1.82, .128), (1.875, .123), (1.93, .086), (1.959, .010)]

    def sculpt(x, z):
        # A single manifold surface contains the nose bridge, alar base, brow,
        # eye sockets, cheek pads, nasolabial transition, and rounded chin.
        d = 0.0
        for sign in (-1, 1):
            d -= (.0055 if glasses else .0075) * _gaussian(x, z, sign * .068 * scale, 1.774, .042 * scale, .042)
            d += .0070 * _gaussian(x, z, sign * eye_x, eye_z, .026 * scale, .017)
            d -= .0045 * _gaussian(x, z, sign * eye_x, eye_z + .024, .030 * scale, .011)
            d += .0013 * _gaussian(x, z, sign * .041 * scale, 1.735, .014 * scale, .028)
            d += .0035 * _gaussian(x, z, sign * .108 * scale, 1.824, .018 * scale, .029)
        d -= .021 * _gaussian(x, z, 0, 1.807, .0135 * scale, .047)
        d -= (.047 if glasses else .043) * _gaussian(x, z, .001 * scale, 1.771, .021 * scale, .014)
        d -= .006 * _gaussian(x, z, 0, 1.737, .042 * scale, .030)
        d -= .005 * _gaussian(x, z, 0, 1.661, .042 * scale, .018)
        return d

    def face_y(x, z):
        w = _lerp_table(z, width) * scale
        cosine = math.sqrt(max(0, 1 - (x / max(w, .001)) ** 2))
        return .010 - _lerp_table(z, front) * scale * cosine + sculpt(x, z) * cosine ** 4

    verts, faces, uv = [], [], []
    rings, sides = 42, 64
    for j in range(rings + 1):
        z = 1.625 + (1.959 - 1.625) * j / rings
        w = _lerp_table(z, width) * scale
        for i in range(sides):
            a = TAU * i / sides
            c = math.cos(a)
            lower_jaw = max(0, 1 - j / 9)
            rear = (1 - max(0, c))
            x = (w + .018 * scale * lower_jaw * rear) * math.sin(a)
            y = .010 - _lerp_table(z, front if c >= 0 else back) * scale * c
            if c > 0:
                y += sculpt(x, z) * c ** 4
            verts.append((x, y, z - .016 * lower_jaw * rear))
            uv.append((i / sides, j / rings))
    for j in range(rings):
        for i in range(sides):
            a, b = j * sides + i, j * sides + (i + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.extend([tuple(reversed(range(sides))), tuple(rings * sides + i for i in range(sides))])
    api.mesh(prefix + '_Sculpted_face', verts, faces, 'skin', HEAD, uv)

    def neck_weights(co):
        h = max(0, min(1, (co.z - 1.61) / .079))
        return {NECK: 1 - h, HEAD: h}

    api.tube(prefix + '_Neck', [(0, .038, z) for z in (1.545, 1.577, 1.606, 1.640, 1.667)],
             [(.074 if glasses else .085, .061), (.070 if glasses else .080, .059),
              (.063 if glasses else .074, .057), (.058 if glasses else .068, .054), (.058 if glasses else .069, .054)],
             'skin', NECK, 32, neck_weights)

    _build_ears(api, prefix, width, scale)
    _build_eyes(api, prefix, face_y, eye_x, eye_z, glasses, scale)
    _build_nose_and_lips(api, prefix, face_y, mouth_z, glasses, scale)
    _build_hair(api, prefix, glasses, scale)
    if glasses:
        _build_glasses(api, prefix, scale)


def _build_ears(api, prefix, widths, scale):
    for sign, label in ((-1, 'L'), (1, 'R')):
        cx = sign * (_lerp_table(1.787, widths) * scale + .010 * scale)
        cy, cz = .001, 1.785

        def point(q, z, depth=0):
            return (cx + sign * q * .84, cy - q * .48 + depth, cz + z)

        verts, faces, uv = [], [], []
        sides, rows = 24, 4
        # Two surfaces give the pinna/lobe actual thickness. The front bowl
        # curves inward rather than reading as an extra sphere on the head.
        for side in range(2):
            for row in range(rows + 1):
                r = max(.002, row / rows)
                for i in range(sides):
                    a = TAU * i / sides
                    q = .022 * scale * r * math.cos(a) * (1 + .08 * math.sin(a))
                    zz = .039 * r * math.sin(a)
                    depth = (-.003 + .009 * (1 - r) ** 2) if side == 0 else (.007 + .003 * (1 - r))
                    verts.append(point(q, zz, depth))
                    uv.append((.5 + q / (.05 * scale), .5 + zz / .083))
        plane = (rows + 1) * sides
        for side in range(2):
            for row in range(rows):
                for i in range(sides):
                    a = side * plane + row * sides + i
                    b = side * plane + row * sides + (i + 1) % sides
                    face = (a, b, b + sides, a + sides)
                    outward_front = face if sign < 0 else tuple(reversed(face))
                    faces.append(outward_front if side == 0 else tuple(reversed(outward_front)))
        for i in range(sides):
            a = rows * sides + i
            b = rows * sides + (i + 1) % sides
            faces.append((a, b, b + plane, a + plane))
        api.mesh(prefix + '_Ear_' + label, verts, faces, 'skin', HEAD, uv)
        helix = []
        for i in range(25):
            a = TAU * i / 24
            helix.append(point(.020 * scale * math.cos(a) * (1 + .08 * math.sin(a)), .036 * math.sin(a), -.006))
        api.tube(prefix + '_Helix_' + label, helix, [.0028 * scale] * len(helix), 'skin', HEAD, 5)
        antihelix = [point(-.010 * scale, -.018, -.006), point(.003 * scale, -.011, -.007),
                     point(.008 * scale, .001, -.007), point(.007 * scale, .019, -.007),
                     point(-.001 * scale, .028, -.006)]
        api.curve(prefix + '_Antihelix_' + label, antihelix, .0025 * scale, 'skin', HEAD, 10, 5)
        # Dark inner rim supplies depth without large conspicuous black holes.
        concha = [point(-.006 * scale, -.008, -.006), point(.001 * scale, -.005, -.007),
                  point(.002 * scale, .007, -.006), point(-.006 * scale, .012, -.006)]
        api.curve(prefix + '_Concha_' + label, concha, .0023 * scale, 'skin_shadow', HEAD, 8, 5)


def _build_eyes(api, prefix, face_y, eye_x, eye_z, glasses, scale):
    iris_verts, iris_faces, iris_uv = [], [], []
    pupil_verts, pupil_faces, pupil_uv = [], [], []
    for sign, label in ((-1, 'L'), (1, 'R')):
        ex, ez = sign * eye_x, eye_z + (.001 if sign < 0 else 0)
        ew, eh = .0235 * scale, .0046 if glasses else .0041
        ey = face_y(ex, ez) - .0011
        verts, faces, uv = [], [], []
        rows, sides = 4, 24
        for row in range(rows + 1):
            r = max(.002, row / rows)
            for i in range(sides):
                a = TAU * i / sides
                # The pointed almond corners and shallow convex eye patch sit
                # inside the sculpted socket, with no large round eyeball bulge.
                q = ew * r * math.cos(a)
                zz = eh * r * math.sin(a) * (.64 + .36 * abs(math.sin(a))) + .018 * q
                y = ey - .0034 * math.sqrt(max(0, 1 - r * r))
                verts.append((ex + q, y, ez + zz))
                uv.append((.5 + q / (2 * ew), .5 + zz / (2 * eh)))
        for row in range(rows):
            for i in range(sides):
                a, b = row * sides + i, row * sides + (i + 1) % sides
                faces.append((a, a + sides, b + sides, b))
        api.mesh(prefix + '_Eye_white_' + label, verts, faces, 'eye_white', HEAD, uv)
        for name, radius, depth, vv, ff, uu in (
                ('iris', .0063 * scale, .0040, iris_verts, iris_faces, iris_uv),
                ('pupil', .00265 * scale, .00445, pupil_verts, pupil_faces, pupil_uv)):
            offset = len(vv)
            vv.append((ex + .001 * sign, ey - depth, ez))
            uu.append((.5, .5))
            for i in range(33):
                a = TAU * i / 32
                q = .001 * sign + radius * math.cos(a)
                corner = math.sqrt(max(0, 1 - (q / ew) ** 2))
                limit = eh * corner * (.64 + .36 * corner)
                zz = max(-limit + .0002, min(limit - .0002, radius * math.sin(a))) + .018 * q
                vv.append((ex + q, ey - depth + .00025, ez + zz))
                uu.append((.5 + .5 * math.cos(a), .5 + .5 * math.sin(a)))
            for i in range(32):
                ff.append((offset, offset + i + 1, offset + i + 2))
        for upper in (True, False):
            points, radii = [], []
            for j in range(13):
                t = j / 12
                q = (t * 2 - 1) * ew
                zz = (1 if upper else -1) * eh * math.sin(math.pi * t) + .018 * q
                y = ey - .0005 - .0029 * math.sin(math.pi * t)
                points.append((ex + q, y, ez + zz))
                radii.append((.00065 + .00030 * math.sin(math.pi * t)) * scale)
            api.tube(prefix + ('_Upper_lid_' if upper else '_Lower_lid_') + label,
                     points, radii, 'skin', HEAD, 5)
            # A soft skin strip overlaps the iris edge like an eyelid. This
            # also bridges the patch to the surrounding sculpted socket.
            verts, faces, uv = [], [], []
            for row in range(3):
                r = row / 2
                for j in range(17):
                    t = j / 16
                    q = (2 * t - 1) * ew
                    arc = math.sin(math.pi * t)
                    zz = (1 if upper else -1) * (eh * arc + .0030 * arc * r) + .018 * q
                    outer_y = face_y(ex + q, ez + zz) - .0007
                    inner_y = ey - .0005 - .0029 * arc
                    verts.append((ex + q, inner_y * (1 - r) + outer_y * r, ez + zz))
                    uv.append((t, r))
            for row in range(2):
                for j in range(16):
                    a = row * 17 + j
                    f = (a, a + 1, a + 18, a + 17)
                    faces.append(f if upper else tuple(reversed(f)))
            api.mesh(prefix + ('_Upper_eyelid_skin_' if upper else '_Lower_eyelid_skin_') + label,
                     verts, faces, 'skin', HEAD, uv)
        # Brow shape is separate from the forehead sculpture and follows a
        # subtle asymmetric expression rather than a painted horizontal bar.
        points, radii = [], []
        for j in range(13):
            t = j / 12
            x = ex + (2 * t - 1) * .029 * scale
            z = ez + .025 + .004 * math.sin(math.pi * t) - .025 * sign * (x - ex)
            points.append((x, face_y(x, z) - .0025, z))
            radii.append((.0008 + .0018 * math.sin(math.pi * t) ** .7) * scale)
        api.tube(prefix + '_Eyebrow_' + label, points, radii, 'hair', HEAD, 5)
        under_eye = []
        for j in range(11):
            t = j / 10
            x = ex + (2 * t - 1) * .021 * scale
            z = ez - .014 - .002 * math.sin(math.pi * t)
            under_eye.append((x, face_y(x, z) - .0008, z))
        api.tube(prefix + '_Under_eye_fold_' + label, under_eye, [.00065 * scale] * len(under_eye), 'skin_shadow', HEAD, 4)
    api.mesh(prefix + '_Irises', iris_verts, iris_faces, 'iris', HEAD, iris_uv)
    api.mesh(prefix + '_Pupils', pupil_verts, pupil_faces, 'pupil', HEAD, pupil_uv)


def _build_nose_and_lips(api, prefix, face_y, mouth_z, glasses, scale):
    # Small alar folds and nostrils supplement the nose already formed in the
    # continuous face mesh; there is no primitive stuck to a flat forehead.
    for sign, label in ((-1, 'L'), (1, 'R')):
        x, z = sign * .016 * scale, 1.762
        y = face_y(x, z)
        api.ellipsoid(prefix + '_Nostril_' + label, (x, y - .0017, z),
                      (.0053 * scale, .0025, .0026), 'skin_shadow', HEAD, 2)
        points = []
        for j in range(9):
            a = math.pi * (.1 + .9 * j / 8)
            xx, zz = x + sign * .006 * scale * math.cos(a), z + .007 * math.sin(a)
            points.append((xx, face_y(xx, zz) - .001, zz))
        api.tube(prefix + '_Nasal_fold_' + label, points, [.0006] * len(points), 'skin_shadow', HEAD, 4)
    mw = (.033 if glasses else .038) * scale
    # A tiny mouth slit avoids conspicuous teeth; two shaped lip strips contain
    # a cupid's bow and rounded lower lip, with a faint uneven smile.
    slit_verts, slit_uv = [], []
    for j in range(25):
        t = j / 24
        x = (2 * t - 1) * mw
        arc = math.sin(math.pi * t)
        z = mouth_z + .020 * x + .002 * (1 - arc)
        for dz in (-.0017 * arc, .0014 * arc):
            slit_verts.append((x, face_y(x, z) - .0027, z + dz))
            slit_uv.append((t, 0 if dz < 0 else 1))
    slit_faces = [(2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2) for j in range(24)]
    api.mesh(prefix + '_Mouth_slit', slit_verts, slit_faces, 'skin_shadow', HEAD, slit_uv)
    for upper in (True, False):
        verts, faces, uv = [], [], []
        for row in range(4):
            r = row / 3
            for j in range(25):
                t = j / 24
                x = (2 * t - 1) * mw
                arc = math.sin(math.pi * t)
                cz = mouth_z + .020 * x + .002 * (1 - arc)
                cupid = .002 * (math.exp(-((t - .38) / .10) ** 2) + math.exp(-((t - .62) / .10) ** 2))
                band = (.0055 * arc + cupid) if upper else (.0067 * arc)
                z = cz + (1 if upper else -1) * (.0015 * arc + band * r)
                y = face_y(x, z) - .0015 - (.0027 if upper else .0033) * arc * math.sin(math.pi * r)
                verts.append((x, y, z))
                uv.append((t, r))
        for row in range(3):
            for j in range(24):
                a = row * 25 + j
                face = (a, a + 1, a + 26, a + 25)
                faces.append(face if upper else tuple(reversed(face)))
        api.mesh(prefix + ('_Upper_lip' if upper else '_Lower_lip'), verts, faces, 'lips', HEAD, uv)


def _build_glasses(api, prefix, scale):
    verts, faces, uv = [], [], []
    for sign in (-1, 1):
        points = []
        for i in range(33):
            a = TAU * i / 32
            # Mild superellipse: rounded thin metal frames like the motif.
            x = sign * .0435 * scale + .0345 * scale * math.copysign(abs(math.cos(a)) ** .82, math.cos(a))
            z = 1.814 + .0205 * math.copysign(abs(math.sin(a)) ** .82, math.sin(a))
            y = -.158 + .021 * (abs(x) / (.125 * scale)) ** 2
            points.append((x, y, z))
        _tube_append(verts, faces, uv, points, [.0010 * scale] * len(points), 5)
        # Two-stage bent temples sit outside the cheek and then hook around
        # the ears, rather than disappearing into the face silhouette.
        points = [(sign * .077 * scale, -.147, 1.821),
                  (sign * .106 * scale, -.109, 1.821),
                  (sign * .126 * scale, -.046, 1.814),
                  (sign * .132 * scale, .010, 1.802),
                  (sign * .129 * scale, .030, 1.785)]
        _tube_append(verts, faces, uv, points, [.00115 * scale] * len(points), 5)
    bridge = [(-.009 * scale, -.157, 1.821), (-.006 * scale, -.169, 1.827),
              (0, -.178, 1.829), (.006 * scale, -.169, 1.827), (.009 * scale, -.157, 1.821)]
    _tube_append(verts, faces, uv, bridge, [.0011 * scale] * len(bridge), 5)
    api.mesh(prefix + '_Thin_metal_glasses', verts, faces, 'metal', HEAD, uv)


def _build_hair(api, prefix, glasses, scale):
    rng = random.Random(810 if glasses else 811)
    sides, rows = 54, 15
    verts, faces, uv = [], [], []

    def limit(theta):
        frontness = max(0, math.cos(theta))
        backness = max(0, -math.cos(theta))
        boundary = (1.72 if glasses else 1.76) - (.56 if glasses else .64) * frontness + .11 * backness
        return boundary + (.022 if glasses else .009) * math.sin(theta * 7 + .7) * frontness

    def scalp(theta, phi, lift=0):
        # The longer hairstyle has uneven, thick swept volume. The cropped
        # sides fit almost flush to the skull but the top remains broad/full.
        top = math.exp(-((phi - .70) / .58) ** 2)
        rx = ((.130 + .004 * top) if glasses else (.127 + .013 * top)) * scale
        ry = ((.148 if glasses else .148) if math.cos(theta) >= 0 else .132) * scale
        crest = .005 * math.sin(phi) * max(0, math.sin(theta)) if glasses else .002 * top
        rough = (.0017 if glasses else .0007) * math.sin(theta * 13 + phi * 9) * math.sin(phi * 11 - theta * 3)
        point = (rx * math.sin(phi) * math.sin(theta),
                 .010 - ry * math.sin(phi) * math.cos(theta),
                 1.803 + .168 * math.cos(phi) + crest)
        normal = _unit((point[0], point[1] - .010, (point[2] - 1.803) * .80))
        return tuple(point[k] + normal[k] * (rough + lift) for k in range(3))

    for row in range(rows + 1):
        t = row / rows
        for i in range(sides):
            theta = TAU * i / sides
            phi = .025 + (limit(theta) - .025) * t
            x, y, z = scalp(theta, phi)
            z += t ** 7 * .002 * math.sin(theta * 11 + .6)
            verts.append((x, y, z))
            uv.append((i / sides, t))
    for row in range(rows):
        for i in range(sides):
            a, b = row * sides + i, row * sides + (i + 1) % sides
            faces.append((a, a + sides, b + sides, b))
    faces.append(tuple(range(sides)))
    api.mesh(prefix + ('_Swept_hair_mass' if glasses else '_Close_cropped_scalp'), verts, faces, 'hair', HEAD, uv)

    # Dense flat locks share ONE mesh. Their raised centre is under 1mm, so
    # highlights describe fine hair flow rather than a handful of shiny pipes.
    verts, faces, uv = [], [], []
    count = 108 if glasses else 122
    for i in range(count):
        theta = TAU * (i / count) + rng.uniform(-.12, .12)
        phi = rng.uniform(.08, min(1.38 if glasses else 1.20, limit(theta) - .13))
        sweep = -rng.uniform(.19, .43) if glasses else rng.uniform(-.025, .08)
        span = rng.uniform(.23, .39) if glasses else rng.uniform(.12, .22)
        points, widths = [], []
        for j in range(5):
            t = j / 4
            th = theta + sweep * t
            pp = min(limit(th) - .008, phi + span * t)
            lift = .0008 + (.0014 if glasses else .0021) * math.sin(math.pi * t)
            points.append(scalp(th, pp, lift))
            widths.append((.00155 if glasses else .00115) * scale * (.30 + .70 * math.sin(math.pi * t) ** .65) * (1 - .66 * t))
        _ribbon_append(verts, faces, uv, points, widths, .00065 if glasses else .00045)
    if glasses:
        # Uneven flat fringe clusters cross the forehead. Their ends interleave
        # closely instead of leaving broad bare areas between isolated tubes.
        for i in range(38):
            theta = -.76 + i * .043 + rng.uniform(-.016, .016)
            points, widths = [], []
            for j in range(5):
                t = j / 4
                th = theta - .24 * t
                phi = .66 + (.52 + .020 * math.sin(i * 1.8)) * t
                p = scalp(th, min(phi, limit(th) + .021), .0012 + .0015 * math.sin(math.pi * t))
                points.append((p[0], p[1] - .0005, p[2] - .004 * t))
                widths.append(.0019 * scale * (1 - .94 * t))
            _ribbon_append(verts, faces, uv, points, widths, .0007)
    else:
        # Very short fine strokes on the sides read as the clipper fade. They
        # follow the skull and add almost no extra silhouette volume.
        for i in range(48):
            theta = TAU * i / 48 + rng.uniform(-.03, .03)
            if limit(theta) < 1.28:
                continue
            phi = rng.uniform(1.17, max(1.18, limit(theta) - .055))
            points, widths = [], []
            for j in range(5):
                t = j / 4
                points.append(scalp(theta + .015 * t, min(limit(theta) - .002, phi + .085 * t), .00045))
                widths.append(.00062 * scale * (1 - .86 * t))
            _ribbon_append(verts, faces, uv, points, widths, .0003)
    # A few very fine broken silhouette wisps retain the tousled motif. Flat
    # tapered strips and restrained length avoid the old comb/spaghetti look.
    for i in range(18 if glasses else 14):
        theta = TAU * i / (18 if glasses else 14) + rng.uniform(-.05, .05)
        phi = rng.uniform(.20, 1.12 if glasses else .87)
        points, widths = [], []
        for j in range(5):
            t = j / 4
            pp = phi + (.18 if glasses else .11) * t
            th = theta - (.14 if glasses else .035) * t
            lift = .0008 + (.008 if glasses else .005) * math.sin(math.pi * t / 2)
            points.append(scalp(th, pp, lift))
            widths.append((.0008 if glasses else .00065) * scale * (1 - .96 * t))
        _ribbon_append(verts, faces, uv, points, widths, .00035)
    api.mesh(prefix + '_Batched_hair_locks', verts, faces, 'hair', HEAD, uv)
