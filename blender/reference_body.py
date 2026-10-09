"""Photo-motif male pursuer bodies, measured in metres and facing Blender -Y.

The public entry point is ``build_body(api, profile)``.  The caller owns the
materials, the rig and export.  All geometry is original; badges deliberately
use abstract marks rather than the photograph's names or official insignia.
"""
import math


def _value(profile, key, default):
    if isinstance(profile, dict):
        return profile.get(key, default)
    return getattr(profile, key, default)


def build_body(api, profile):
    """Build one clothed body against the shared 20-bone reference skeleton.

    Height scaling belongs to the caller, so both variants share animation
    landmarks. ``width`` changes the shirt, trousers and soft tissue, while
    ``shoulder`` follows the corresponding variant's upper-arm bone location.
    """
    mesh = api['mesh'] if isinstance(api, dict) else api.mesh
    tube = api['tube'] if isinstance(api, dict) else api.tube
    primitive_curve = api['curve'] if isinstance(api, dict) else api.curve
    primitive_block = api['block'] if isinstance(api, dict) else api.block
    ellipsoid = api['ellipsoid'] if isinstance(api, dict) else api.ellipsoid
    variant = _value(profile, 'id', 'glasses')
    width = float(_value(profile, 'width', 1.0))
    shoulder = float(_value(profile, 'shoulder', .275))
    prefix = variant + '_'
    stocky = variant == 'cropped'
    finger_rig = bool(_value(profile, 'finger_rig', False))
    waist_bulk = 1.15 if stocky else 1.035
    depth_bulk = 1.19 if stocky else 1.02
    arm_width = width * (1.075 if stocky else 1.0)

    def curve(name, points, radius, material, bone, samples=20, sides=8, weights=None):
        # These curves are fine seams, laces or modest folds. Ten interpolated
        # segments and five radial sides remain smooth at mobile viewing size.
        return primitive_curve(name, points, radius, material, bone,
                               min(samples, 10), min(sides, 5), weights)

    def block(name, center, dims, material, bone, bevel=0, rotation=(0, 0, 0)):
        # Submillimetre badge/ID marks are texture-scale detail, so their edge
        # bevels would multiply the count without changing visible silhouettes.
        if max(dims) < .09 or bevel < .003:
            bevel = 0
        return primitive_block(name, center, dims, material, bone, bevel, rotation)

    def clamp(v):
        return max(0.0, min(1.0, v))

    def torso_weights(co):
        # Blend the tucked hem into the pelvis instead of opening a waist gap.
        w = clamp((co.z - .95) / .17)
        return {'HIPS_CTRL': 1.0 - w, 'TORSO_CTRL': w}

    def neck_weights(co):
        w = clamp((co.z - 1.495) / .11)
        return {'TORSO_CTRL': 1.0 - w, 'NECK_CTRL': w}

    def rings(name, profiles, material, bone, sides=40, weights=None,
              center=(0, 0), exponent=1.0, fold=0, notch=False):
        """Closed oval surface with connected UVs and restrained fabric folds."""
        vertices, faces, uvs = [], [], []
        for row, (z, rx, ry) in enumerate(profiles):
            for col in range(sides + 1):
                angle = math.tau * col / sides
                ca, sa = math.cos(angle), math.sin(angle)
                cx = math.copysign(abs(ca) ** exponent, ca)
                cy = math.copysign(abs(sa) ** exponent, sa)
                wrinkle = fold * math.cos(angle * 10 + row * .72)
                x = center[0] + (rx + wrinkle) * cx
                y = center[1] + (ry + wrinkle * .65) * cy
                zz = z + fold * .7 * math.sin(angle * 7 + row * .91)
                if notch and z > 1.47:
                    # The front neckline descends into the open collar.
                    zz -= .074 * clamp((z - 1.47) / .075) * max(0, -sa) ** 7
                vertices.append((x, y, zz))
                uvs.append((col / sides, row / (len(profiles) - 1)))
        stride = sides + 1
        for row in range(len(profiles) - 1):
            for col in range(sides):
                a = row * stride + col
                faces.append((a, a + 1, a + stride + 1, a + stride))
        # The last ring stays open for a shirt/neck collar; trouser and shoe
        # ends are capped.  The neck and head overlap inside the collar.
        faces.append(tuple(reversed(range(sides))))
        if not notch:
            faces.append(tuple((len(profiles) - 1) * stride + n for n in range(sides)))
        return mesh(prefix + name, vertices, faces, material, bone, uvs, weights)

    def panel(name, vertices, material='cloth', bone='TORSO_CTRL', depth=.003):
        """A slightly thickened fabric panel avoids back-face gaps at folds."""
        n = len(vertices)
        verts = list(vertices) + [(x, y + depth, z) for x, y, z in vertices]
        faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, j + n, i + n))
        return mesh(prefix + name, verts, faces, material, bone,
                    [(i % n / max(n - 1, 1), i // n) for i in range(2 * n)])

    def strap(name, points, ribbon_width, material='moss', bone='TORSO_CTRL'):
        verts, faces, uvs = [], [], []
        for row, (x, y, z) in enumerate(points):
            before = points[max(0, row - 1)]
            after = points[min(len(points) - 1, row + 1)]
            dx, dz = after[0] - before[0], after[2] - before[2]
            length = max(math.hypot(dx, dz), .0001)
            nx, nz = -dz / length * ribbon_width * .5, dx / length * ribbon_width * .5
            for depth in [-.0011, .0011]:
                verts.extend([(x + nx, y + depth, z + nz),
                              (x - nx, y + depth, z - nz)])
                uvs.extend([(0, row / (len(points) - 1)), (1, row / (len(points) - 1))])
        for row in range(len(points) - 1):
            a, b = row * 4, (row + 1) * 4
            faces.extend([(a, b, b + 1, a + 1), (a + 2, a + 3, b + 3, b + 2),
                          (a, a + 2, b + 2, b), (a + 1, b + 1, b + 3, a + 3)])
        faces.extend([(0, 1, 3, 2), tuple(range(len(verts) - 4, len(verts)))])
        return mesh(prefix + name, verts, faces, material, bone, uvs)

    # Skin at the V-neck is intentionally attached to torso and neck bones.
    rings('Exposed_open_neck', [(1.445, .067, .063), (1.47, .079, .071),
                              (1.505, .074, .069), (1.545, .067, .064),
                              (1.585, .065, .063), (1.62, .068, .065),
                              (1.655, .075, .066)],
          'skin', 'NECK_CTRL', 24, neck_weights, center=(0, -.002))

    shirt = [(.945, .183 * width * waist_bulk, .121 * width * depth_bulk),
             (.970, .190 * width * waist_bulk, .128 * width * depth_bulk),
             (1.000, .195 * width * waist_bulk, .132 * width * depth_bulk),
             (1.045, .194 * width * waist_bulk, .134 * width * depth_bulk),
             (1.095, .199 * width * waist_bulk, .139 * width * depth_bulk),
             (1.150, .210 * width * (waist_bulk - .02), .144 * width * depth_bulk),
             (1.210, .222 * width * (waist_bulk - .045), .145 * width * depth_bulk),
             (1.270, .236 * width * (1.055 if stocky else 1.0), .146 * width * depth_bulk),
             (1.325, .248 * width * (1.025 if stocky else 1.0), .144 * width * depth_bulk),
             (1.380, .258 * width, .140 * width * depth_bulk),
             (1.425, .261 * width, .132 * width * (1.10 if stocky else 1.0)),
             (1.465, shoulder * .97, .119 * width),
             (1.492, shoulder * .78, .101 * width),
             (1.518, .145 * width, .086 * width),
             (1.545, .080 * width, .075 * width)]
    rings('Tailored_short_sleeve_shirt', shirt, 'cloth', 'TORSO_CTRL', 48,
          torso_weights, center=(0, .007), exponent=.80, fold=.0016, notch=True)

    # Shirt front surface approximation for raised stitching and pocket panels.
    def front_y(x, extra=.002, z=1.27):
        lo, hi = shirt[0], shirt[-1]
        for first, second in zip(shirt, shirt[1:]):
            if first[0] <= z <= second[0]:
                lo, hi = first, second
                break
        t = clamp((z - lo[0]) / max(.0001, hi[0] - lo[0]))
        rx = lo[1] + (hi[1] - lo[1]) * t
        ry = lo[2] + (hi[2] - lo[2]) * t
        cosine = min(.999, (abs(x) / rx) ** (1 / .80))
        return .007 - ry * max(.0001, 1 - cosine * cosine) ** (.80 / 2) - extra

    # Open V collar: full front leaves and a small collar stand on the back.
    for side, sign in [('L', -1), ('R', 1)]:
        panel('Pointed_collar_' + side,
              [(sign * .027, -.094, 1.508), (sign * .065, -.079, 1.554),
               (sign * .127, -.104, 1.499), (sign * .096, -.162, 1.422),
               (sign * .036, -.148, 1.472)])
        curve(prefix + 'Collar_stitch_' + side,
              [(sign * .061, -.082, 1.551), (sign * .122, -.109, 1.496),
               (sign * .092, -.164, 1.430), (sign * .039, -.150, 1.475)],
              .00045, 'cloth', 'TORSO_CTRL', 16, 5)
    collar_points = [(.075 * math.cos(a), .075 * math.sin(a), 1.553)
                     for a in [i * math.pi / 16 for i in range(17)]]
    tube(prefix + 'Back_collar_stand', collar_points,
         [(.015, .005)] * len(collar_points), 'cloth', 'NECK_CTRL', 8,
         neck_weights)

    # Placket follows the central front. Buttons are golden off-white, not
    # floating grey blobs, and have two small modeled holes.
    placket_vertices, placket_uv = [], []
    placket_z = [.986, 1.025, 1.08, 1.15, 1.22, 1.28, 1.34, 1.40, 1.425]
    for row, z in enumerate(placket_z):
        for x in [-.012, .012]:
            placket_vertices.append((x, front_y(x, .003, z), z))
            placket_uv.append((0 if x < 0 else 1, row / (len(placket_z) - 1)))
    mesh(prefix + 'Raised_front_placket', placket_vertices,
         [(2 * row, 2 * row + 1, 2 * row + 3, 2 * row + 2)
          for row in range(len(placket_z) - 1)], 'cloth', 'TORSO_CTRL',
         placket_uv, torso_weights)
    for sign in [-1, 1]:
        curve(prefix + 'Placket_stitch_' + str(sign),
              [(sign * .009, front_y(0, .004, z), z) for z in placket_z],
              .0004, 'cloth', 'TORSO_CTRL', 15, 5, torso_weights)
    for row, z in enumerate([1.01, 1.112, 1.216, 1.325, 1.416]):
        ellipsoid(prefix + 'Shirt_button_' + str(row),
                  (0, front_y(0, .009, z), z), (.0052, .0024, .0052),
                  'button', 'TORSO_CTRL', 2)
        for hole in [-1, 1]:
            ellipsoid(prefix + 'Button_hole_' + str(row) + '_' + str(hole),
                      (hole * .00155, front_y(0, .0115, z), z),
                      (.0007, .0005, .0007), 'stitch', 'TORSO_CTRL', 1)

    # Modeled chest pockets: broad planes with a bowed edge, folded flap and
    # outline stitching.  The variants share tailoring but not the markings.
    for side, sign in [('L', -1), ('R', 1)]:
        cx = sign * .123 * width
        pw, low, high = .108 * width, 1.18, 1.312
        vertices, faces, uv = [], [], []
        for row in range(7):
            t = row / 6
            for col in range(9):
                u = col / 8
                x = cx + (u - .5) * pw
                z = low + t * (high - low) - .011 * abs(2 * u - 1) * (1 - t)
                y = front_y(x, .003 + .0018 * math.sin(math.pi * u) * math.sin(math.pi * t), z)
                vertices.append((x, y, z)); uv.append((u, t))
        for row in range(6):
            for col in range(8):
                a = row * 9 + col
                faces.append((a, a + 1, a + 10, a + 9))
        mesh(prefix + 'Chest_pocket_' + side, vertices, faces,
             'cloth', 'TORSO_CTRL', uv)
        edge = [(cx - pw / 2, front_y(cx - pw / 2, .005, high), high),
                (cx - pw / 2, front_y(cx - pw / 2, .005, low), low - .009),
                (cx, front_y(cx, .005, low), low),
                (cx + pw / 2, front_y(cx + pw / 2, .005, low), low - .009),
                (cx + pw / 2, front_y(cx + pw / 2, .005, high), high)]
        curve(prefix + 'Pocket_stitch_' + side, edge, .00045,
              'cloth', 'TORSO_CTRL', 18, 5)
        panel('Pocket_flap_' + side,
              [(cx - pw / 2, front_y(cx - pw / 2, .007, high + .009), high + .009),
               (cx + pw / 2, front_y(cx + pw / 2, .007, high + .009), high + .009),
               (cx + pw / 2, front_y(cx + pw / 2, .009, high - .023), high - .023),
               (cx, front_y(cx, .010, high - .035), high - .035),
               (cx - pw / 2, front_y(cx - pw / 2, .009, high - .023), high - .023)], depth=.002)
        ellipsoid(prefix + 'Pocket_button_' + side,
                  (cx, front_y(cx, .013, high - .024), high - .024), (.004, .002, .004),
                  'button', 'TORSO_CTRL', 1)

    # Small cloth creases rise from the tucked waist and sleeve seam.  Most
    # detail comes from the atlas rather than expensive disconnected objects.
    for sign in [-1, 1]:
        for row in range(3):
            z = 1.03 + row * .049
            curve(prefix + 'Front_tucked_fold_' + str(sign) + '_' + str(row),
                  [(sign * .035, front_y(.035, .0005, z), z),
                   (sign * .097, front_y(.097, .0010, z + .015), z + .015),
                   (sign * .165, front_y(.165, .0005, z + .009), z + .009)],
                  .0005, 'cloth', 'TORSO_CTRL', 12, 6, torso_weights)
        curve(prefix + 'Shoulder_tailoring_' + str(sign),
              [(sign * .086, .061, 1.524), (sign * .176, .067, 1.505),
               (sign * (shoulder - .017), .071, 1.468)],
              .00045, 'cloth', 'TORSO_CTRL', 14, 5)
        # Original two diamonds and one band stand in for real shoulder rank.
        px = sign * (shoulder - .072)
        block(prefix + 'Abstract_shoulder_tab_' + str(sign),
              (px, -.012, 1.496), (.098, .071, .012),
              'black', 'TORSO_CTRL', .004, (0, sign * .11, 0))
        block(prefix + 'Shoulder_tab_band_' + str(sign),
              (px - sign * .031, -.012, 1.504), (.004, .052, .002),
              'metal', 'TORSO_CTRL', .0008, (0, sign * .11, 0))
        for n in range(2):
            block(prefix + 'Abstract_tab_diamond_' + str(sign) + '_' + str(n),
                  (px + sign * (.006 + n * .022), -.012, 1.508),
                  (.013, .013, .002), 'metal', 'TORSO_CTRL', .0006,
                  (0, sign * .11, math.pi / 4))

    for side, sign in [('L', -1), ('R', 1)]:
        arm, elbow, hand = 'ARM_' + side + '_CTRL', 'ELBOW_' + side + '_CTRL', 'HAND_' + side + '_CTRL'
        ax = lambda t: sign * (shoulder + .10 * t)

        def arm_weights(co, a=arm, e=elbow, h=hand):
            upper = clamp((co.z - 1.10) / .13)
            hand_part = clamp((.895 - co.z) / .075)
            torso_part = clamp((co.z - 1.425) / .075)
            return {'TORSO_CTRL': torso_part,
                    a: upper * (1 - torso_part),
                    e: (1 - upper) * (1 - hand_part) * (1 - torso_part),
                    h: (1 - upper) * hand_part * (1 - torso_part)}

        def sleeve_weights(co, a=arm):
            # A soft shoulder yoke follows both chest and upper arm rotation.
            upper = clamp((1.50 - co.z) / .075)
            return {'TORSO_CTRL': 1 - upper, a: upper}

        # The skin shoulder cap is recessed under the shirt; putting it on the
        # sleeve's first plane causes a visible skin-coloured disk / Z fighting.
        arm_points = [(ax(t), .003, 1.458 - .298 * t)
                      for t in [0, .10, .24, .38, .52, .68, .83, 1.0]]
        arm_radii = [(.064 * arm_width, .066 * arm_width), (.066 * arm_width, .062 * arm_width),
                     (.063 * arm_width, .058 * arm_width), (.059 * arm_width, .054 * arm_width),
                     (.057 * arm_width, .052 * arm_width), (.055 * arm_width, .048 * arm_width),
                     (.051 * arm_width, .046 * arm_width), (.047 * arm_width, .043 * arm_width)]
        forearm_points = [(sign * (shoulder + .10 + .03 * t), .002,
                           1.16 - .315 * t)
                          for t in [.13, .25, .38, .53, .68, .81, .92, 1.0]]
        forearm_radii = [(.051 * arm_width, .045 * arm_width), (.055 * arm_width, .047 * arm_width),
                         (.055 * arm_width, .045 * arm_width), (.050 * arm_width, .042 * arm_width),
                         (.042 * arm_width, .036 * arm_width), (.033 * arm_width, .029 * arm_width),
                         (.027 * width, .024 * width), (.025 * width, .023 * width)]
        # One continuous skin tube through the elbow eliminates a ball-joint
        # outline and lets the interpolated weights distribute the bend.
        tube(prefix + 'Anatomical_arm_' + side,
             arm_points + forearm_points, arm_radii + forearm_radii,
             'skin', arm, 24, arm_weights)

        sleeve_t = [0, .07, .17, .29, .40, .50, .59, .66, .71]
        sleeve_points = [(ax(t) - sign * .031 * (1 - t / .71), .004,
                          1.483 - .323 * t) for t in sleeve_t]
        sleeve_radii = [(.083 * width, .082 * width), (.091 * width, .084 * width),
                        (.095 * width, .082 * width), (.092 * width, .079 * width),
                        (.087 * width, .077 * width), (.082 * width, .074 * width),
                        (.081 * width, .073 * width), (.082 * width, .075 * width),
                        (.080 * width, .074 * width)]
        tube(prefix + 'Short_shirt_sleeve_' + side, sleeve_points, sleeve_radii,
             'cloth', arm, 32, sleeve_weights)
        # An inner facing closes the fabric thickness at the open sleeve edge.
        end = sleeve_points[-1]
        tube(prefix + 'Sleeve_cuff_facing_' + side,
             [(end[0] - sign * .002, end[1], end[2] + .007), end,
              (end[0] + sign * .002, end[1], end[2] - .008)],
             [(.081 * width, .075 * width), (.081 * width, .075 * width),
              (.078 * width, .072 * width)], 'cloth', arm, 32, sleeve_weights)
        # Cuff stitching lies on the visible front circumference.
        cuff_stitch = []
        for n in range(15):
            a = math.pi * n / 14
            cuff_stitch.append((end[0] + .078 * width * math.cos(a),
                                -.072 * width * math.sin(a),
                                end[2] + .009 + sign * .014 * math.cos(a)))
        tube(prefix + 'Cuff_stitch_' + side, cuff_stitch,
             [.0004] * len(cuff_stitch), 'cloth', arm, 5, sleeve_weights)

        wx = sign * (shoulder + .13)
        palm_points = [(wx, -.002, .860), (wx + sign * .003, -.003, .840),
                       (wx + sign * .006, -.004, .815),
                       (wx + sign * .009, -.006, .785),
                       (wx + sign * .010, -.006, .754),
                       (wx + sign * .009, -.007, .735)]
        tube(prefix + 'Structured_palm_' + side, palm_points,
             [(.025 * width, .022 * width), (.029 * width, .023 * width),
              (.038 * width, .025 * width), (.043 * width, .027 * width),
              (.039 * width, .024 * width), (.033 * width, .021 * width)],
             'skin', hand, 20, arm_weights)
        # Four individual digits, rounded fingertips, short nails and knuckle
        # creases. They form a relaxed, slightly cupped hand, not a fist mesh.
        for finger, (offset, length, radius) in enumerate([
                (-.025, .079, .0095), (-.008, .094, .010),
                (.010, .088, .0096), (.027, .070, .0082)]):
            fx = wx + sign * (.008 + offset)
            z0 = .750 - abs(offset) * .12
            points = [(fx, -.007, z0), (fx + sign * .001, -.008, z0 - .013),
                      (fx + sign * .003, -.015, z0 - length * .40),
                      (fx + sign * .005, -.026, z0 - length * .68),
                      (fx + sign * .006, -.037, z0 - length * .87),
                      (fx + sign * .006, -.041, z0 - length),
                      (fx + sign * .006, -.041, z0 - length - .003)]
            radii = [(radius * width, radius * .86 * width),
                     (radius * width, radius * .89 * width),
                     (radius * .94 * width, radius * .84 * width),
                     (radius * .82 * width, radius * .77 * width),
                     (radius * .78 * width, radius * .71 * width),
                     (radius * .63 * width, radius * .56 * width),
                     (.0026, .0024)]
            proximal = f'FINGER_{side}_{finger}_CTRL' if finger_rig else hand
            distal = f'FINGER_{side}_{finger}_TIP_CTRL' if finger_rig else hand

            def digit_weights(co, p=proximal, d=distal, joint=z0 - length * .40):
                if p == d:
                    return {p: 1.0}
                part = clamp((co.z - joint + .0075) / .015)
                return {p: part, d: 1 - part}

            tube(prefix + 'Finger_' + side + '_' + str(finger), points, radii,
                 'skin', proximal, 12, digit_weights)
            block(prefix + 'Short_fingernail_' + side + '_' + str(finger),
                  (fx + sign * .006, -.0475, z0 - length + .012),
                  (radius * 1.15, .0018, .013), 'paper', distal, .0022,
                  (.43, 0, sign * .05))
            for crease in [.37, .67]:
                zz = z0 - length * crease
                yy = -.014 if crease < .5 else -.027
                curve(prefix + 'Finger_crease_' + side + '_' + str(finger) + '_' + str(crease),
                      [(fx - radius * .65, yy - radius * .82, zz),
                       (fx, yy - radius * .98, zz - .001),
                       (fx + radius * .65, yy - radius * .82, zz)],
                      .0004, 'skin_shadow', proximal if crease < .5 else distal, 5, 5,
                      digit_weights)
        tx = wx - sign * .025
        thumb_points = [(tx, -.012, .810), (tx - sign * .014, -.017, .795),
                        (tx - sign * .024, -.029, .773),
                        (tx - sign * .023, -.042, .753),
                        (tx - sign * .019, -.047, .744),
                        (tx - sign * .018, -.047, .741)]
        thumb_proximal = f'THUMB_{side}_CTRL' if finger_rig else hand
        thumb_distal = f'THUMB_{side}_TIP_CTRL' if finger_rig else hand

        def thumb_weights(co, p=thumb_proximal, d=thumb_distal):
            if p == d:
                return {p: 1.0}
            part = clamp((co.z - .773 + .0075) / .015)
            return {p: part, d: 1 - part}

        tube(prefix + 'Opposable_thumb_' + side, thumb_points,
             [(.015 * width, .012 * width), (.014 * width, .012 * width),
              (.012 * width, .011 * width), (.010 * width, .009 * width),
              (.008 * width, .0065 * width), (.003, .003)],
             'skin', thumb_proximal, 12, thumb_weights)
        block(prefix + 'Thumbnail_' + side,
              (tx - sign * .020, -.055, .754), (.013, .002, .016),
              'paper', thumb_distal, .002, (.25, sign * .15, sign * -.17))
        # A subdued tendon ridge joins wrist to knuckles without exposed bones.
        for ridge in [-.018, .011]:
            curve(prefix + 'Hand_tendon_' + side + '_' + str(ridge),
                  [(wx + sign * ridge, -.024, .837),
                   (wx + sign * (ridge + .006), -.030, .790),
                   (wx + sign * (ridge + .011), -.026, .754)],
                  .0011, 'skin', hand, 10, 6)

    # A joined pelvis shell covers the crotch between the two trouser legs.
    def pelvis_weights(co):
        leg_part = .5 * clamp((.965 - co.z) / .12)
        right_part = clamp((co.x / .13 + 1) / 2)
        return {'HIPS_CTRL': 1 - leg_part,
                'THIGH_L_CTRL': leg_part * (1 - right_part),
                'THIGH_R_CTRL': leg_part * right_part}

    rings('Trouser_seat_and_waist', [(.845, .105 * width, .106 * width),
                                   (.873, .160 * width, .115 * width),
                                   (.905, .204 * width, .121 * width),
                                   (.945, .226 * width, .120 * width),
                                   (.985, .229 * width, .121 * width),
                                   (1.015, .222 * width, .121 * width),
                                   (1.040, .213 * width, .117 * width)],
          'trousers', 'HIPS_CTRL', 36, pelvis_weights,
          center=(0, .012), exponent=.86, fold=.001)
    for side, sign in [('L', -1), ('R', 1)]:
        thigh, shin, foot = 'THIGH_' + side + '_CTRL', 'SHIN_' + side + '_CTRL', 'FOOT_' + side + '_CTRL'

        def leg_weights(co, th=thigh, sh=shin):
            pelvis = clamp((co.z - .88) / .16)
            top = clamp((co.z - .455) / .13)
            return {'HIPS_CTRL': pelvis, th: (1 - pelvis) * top,
                    sh: (1 - pelvis) * (1 - top)}

        heights = [.125, .151, .181, .227, .285, .343, .409, .458,
                   .495, .526, .557, .593, .643, .704, .765, .825,
                   .876, .925, .971, 1.01]
        widths = [.070, .073, .075, .075, .077, .080, .083, .087,
                  .090, .088, .091, .094, .098, .103, .108, .114,
                  .118, .123, .124, .122]
        depths = [.072, .073, .077, .078, .080, .083, .085, .088,
                  .090, .093, .096, .098, .103, .108, .110, .112,
                  .114, .116, .117, .116]
        rings('Tailored_trouser_leg_' + side,
              [(z, rx * width, ry * width) for z, rx, ry in zip(heights, widths, depths)],
              'trousers', thigh, 32, leg_weights,
              center=(sign * .13, .012), exponent=.89, fold=.0018)
        curve(prefix + 'Trouser_outer_seam_' + side,
              [(sign * (.13 + rx * width + .001), .015, z)
               for z, rx in zip(heights[1:-1], widths[1:-1])],
              .0005, 'trousers', thigh, 24, 5, leg_weights)
        curve(prefix + 'Pressed_trouser_crease_' + side,
              [(sign * .13, .012 - depths[i] * width - .001, heights[i])
               for i in [1, 3, 5, 8, 10, 13, 16]],
              .0006, 'trousers', thigh, 24, 6, leg_weights)
        # Shallow modeled compression folds at knee and hem.
        for row, z in enumerate([.175, .480, .547]):
            radius = .077 if z < .3 else .09
            curve(prefix + 'Trouser_fold_' + side + '_' + str(row),
                  [(sign * .13 - radius * .8, -.056 * width, z + .004),
                   (sign * .13, -.083 * width, z - .008),
                   (sign * .13 + radius * .8, -.056 * width, z + .004)],
                  .0006, 'trousers', thigh, 12, 6, leg_weights)

        # Structured black leather shoes with separate welt, rounded toe and
        # heel. Feet have real top contours rather than beveled cubes alone.
        shoe_verts, shoe_faces, shoe_uv = [], [], []
        shoe_sections = [(-.245, .017, .066), (-.228, .052, .082),
                         (-.196, .066, .098), (-.153, .069, .110),
                         (-.112, .067, .126), (-.073, .063, .146),
                         (-.035, .058, .158), (.003, .057, .145),
                         (.038, .056, .128), (.067, .043, .102),
                         (.078, .028, .084)]
        sides = 20
        for row, (y, rx, top) in enumerate(shoe_sections):
            for col in range(sides + 1):
                a = math.tau * col / sides
                xx = sign * .13 + rx * math.cos(a)
                # Lower half tapers into the flat sole, upper half has vamp.
                zz = .051 + max(math.sin(a), -.3) * (top - .051)
                shoe_verts.append((xx, y, zz))
                shoe_uv.append((col / sides, row / (len(shoe_sections) - 1)))
        for row in range(len(shoe_sections) - 1):
            for col in range(sides):
                a = row * (sides + 1) + col
                shoe_faces.append((a, a + sides + 1, a + sides + 2, a + 1))
        shoe_faces.extend([tuple(reversed(range(sides))),
                           tuple((len(shoe_sections) - 1) * (sides + 1) + n for n in range(sides))])
        mesh(prefix + 'Rounded_leather_shoe_' + side, shoe_verts, shoe_faces,
             'black', foot, shoe_uv)
        block(prefix + 'Rubber_outsole_' + side, (sign * .13, -.075, .030),
              (.143, .323, .041), 'black', foot, .020)
        block(prefix + 'Shoe_heel_' + side, (sign * .13, .027, .015),
              (.115, .095, .030), 'black', foot, .007)
        # Toe cap seam, a slim leather tongue and crossed laces.
        curve(prefix + 'Toe_cap_seam_' + side,
              [(sign * .13 - .064, -.174, .066),
               (sign * .13 - .044, -.174, .090),
               (sign * .13, -.170, .102),
               (sign * .13 + .044, -.174, .090),
               (sign * .13 + .064, -.174, .066)],
              .0011, 'stitch', foot, 16, 6)
        panel('Leather_tongue_' + side,
              [(sign * .13 - .026, -.134, .119), (sign * .13 + .026, -.134, .119),
               (sign * .13 + .025, -.027, .160), (sign * .13 - .025, -.027, .160)],
              'black', foot, .002)
        for row in range(3):
            y = -.124 + row * .023
            z = .125 + row * .009
            for cross in [-1, 1]:
                curve(prefix + 'Shoelace_' + side + '_' + str(row) + '_' + str(cross),
                      [(sign * .13 - .028, y, z),
                       (sign * .13, y + cross * .007, z + .003),
                       (sign * .13 + .028, y + cross * .012, z + .001)],
                      .0015, 'stitch', foot, 6, 6)

    # Narrow dark belt, stitched loops and a simple original buckle.
    belt_points = [(.216 * width * math.cos(i * math.tau / 32),
                    .013 + .122 * width * math.sin(i * math.tau / 32), 1.033)
                   for i in range(33)]
    tube(prefix + 'Dark_waist_belt', belt_points,
         [(.017, .004)] * len(belt_points), 'black', 'HIPS_CTRL', 6)
    for angle in [.2, 1.2, 2.0, 2.8, 3.9, 5.0]:
        x, y = .222 * width * math.cos(angle), .012 + .124 * width * math.sin(angle)
        block(prefix + 'Belt_loop_' + str(angle), (x, y, 1.035),
              (.012, .007, .055), 'trousers', 'HIPS_CTRL', .002,
              (0, 0, angle - math.pi / 2))
    block(prefix + 'Simple_belt_buckle', (0, -.123 * width, 1.034),
          (.043, .009, .030), 'metal', 'HIPS_CTRL', .003)
    block(prefix + 'Buckle_inset', (0, -.129 * width, 1.034),
          (.028, .003, .017), 'black', 'HIPS_CTRL', .002)

    # Abstract chest plaques and colour bars echo the reference without names,
    # ranks, readable emblems or personal information.
    badge_x = -.121 * width
    block(prefix + 'Abstract_chest_plaque', (badge_x, front_y(badge_x, .016, 1.292), 1.292),
          (.088, .007, .029), 'black', 'TORSO_CTRL', .003)
    for n in range(4):
        block(prefix + 'Plaque_abstract_mark_' + str(n),
              (badge_x - .024 + n * .014, front_y(badge_x, .020, 1.292), 1.292),
              (.007, .0015, .006 if n % 2 else .012),
              'metal', 'TORSO_CTRL', .0005, (0, 0, .12 * n))
    for n, material in enumerate(['red', 'paper', 'blue', 'metal']):
        x = (.098 + n * .010) * width
        block(prefix + 'Abstract_colour_bar_' + str(n),
              (x, front_y(x, .010, 1.346), 1.346), (.009, .005, .018),
              material, 'TORSO_CTRL', .0005)

    # Long woven green lanyard, little sliding keeper, clasp and translucent
    # card-holder rim. The card contains only decorative geometric markings.
    path = [(-.057, -.080, 1.548), (-.077, -.133, 1.471),
            (-.083, -.157 * width, 1.380), (-.074, -.170 * width, 1.291),
            (-.050, -.179 * width, 1.208), (-.007, -.180 * width, 1.156),
            (.037, -.179 * width, 1.186), (.074, -.170 * width, 1.285),
            (.081, -.157 * width, 1.390), (.074, -.133, 1.475),
            (.056, -.080, 1.548)]
    path = [(x, min(y, front_y(x, .010, z)) if z < 1.44 else y, z)
            for x, y, z in path]
    strap('Green_woven_lanyard', path, .0092)
    keeper_y = min(-.172 * width, front_y(.075, .013, 1.351))
    block(prefix + 'Lanyard_sliding_keeper', (.075, keeper_y, 1.351),
          (.014, .009, .029), 'black', 'TORSO_CTRL', .002)
    block(prefix + 'Lanyard_keeper_inset', (.075, keeper_y - .006, 1.351),
          (.007, .002, .014), 'moss', 'TORSO_CTRL', .001)
    clasp_y = min(-.184 * width, front_y(-.007, .015, 1.145))
    block(prefix + 'Metal_card_clasp', (-.007, clasp_y, 1.145),
          (.018, .008, .029), 'metal', 'TORSO_CTRL', .003)
    card_x, card_y, card_z = -.007, min(-.191 * width, front_y(-.007, .018, 1.078)), 1.078
    block(prefix + 'Anonymous_ID_card', (card_x, card_y, card_z),
          (.071, .003, .090), 'paper', 'TORSO_CTRL', .003)
    for label, center, dims in [
            ('Top', (card_x, card_y - .001, card_z + .048), (.084, .007, .006)),
            ('Bottom', (card_x, card_y - .001, card_z - .048), (.084, .007, .006)),
            ('Left', (card_x - .039, card_y - .001, card_z), (.006, .007, .091)),
            ('Right', (card_x + .039, card_y - .001, card_z), (.006, .007, .091))]:
        block(prefix + 'Clear_ID_holder_' + label, center, dims,
              'glass', 'TORSO_CTRL', .0015)
    block(prefix + 'ID_green_header', (card_x, card_y - .003, card_z + .032),
          (.064, .001, .011), 'moss', 'TORSO_CTRL', .001)
    block(prefix + 'ID_abstract_portrait', (card_x - .018, card_y - .003, card_z + .006),
          (.020, .001, .025), 'skin_shadow', 'TORSO_CTRL', .001)
    for row in range(3):
        block(prefix + 'ID_abstract_line_' + str(row),
              (card_x + .012, card_y - .003, card_z + .016 - row * .010),
              (.025 - row * .004, .001, .003), 'stitch', 'TORSO_CTRL', .0005)
    block(prefix + 'ID_green_footer', (card_x, card_y - .003, card_z - .028),
          (.057, .001, .003), 'moss', 'TORSO_CTRL', .0005)

    return {'variant': variant, 'forward': '-Y', 'units': 'metres',
            'body_materials': ['cloth', 'trousers', 'skin', 'skin_shadow',
                               'paper', 'metal', 'moss', 'stitch', 'button',
                               'black', 'red', 'blue', 'glass'],
            'height_scale_owned_by_caller': True}
