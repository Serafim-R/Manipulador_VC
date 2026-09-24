"""Implementação de calibração mão-olho (AX = XB) em NumPy puro.

Serve de fallback para quando `cv2.calibrateHandEye` não está disponível —
é o caso do opencv-contrib-python 5.0.0.93, que exporta as constantes
`cv2.CALIB_HAND_EYE_*` mas não exporta a função em si nos bindings Python.

Se você instalar `opencv-contrib-python<5`, o script principal passa a usar a
implementação oficial do OpenCV automaticamente e este módulo fica ocioso.

Métodos implementados:
  - TSAI  : Tsai & Lenz (1989)
  - PARK  : Park & Martin (1994)
"""

import numpy as np


def _skew(v):
    """Matriz antissimétrica 3x3 do produto vetorial."""
    x, y, z = v.flatten()
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


def _log_rot(R):
    """Rotação 3x3 -> vetor eixo*ângulo (3,)."""
    cos = np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0)
    theta = np.arccos(cos)

    if theta < 1e-12:
        return np.zeros(3)

    if abs(theta - np.pi) < 1e-6:
        # Perto de 180 graus o termo sin(theta) degenera; usa R + I
        A = (R + np.eye(3)) / 2.0
        eixo = np.sqrt(np.clip(np.diag(A), 0.0, None))
        i = int(np.argmax(eixo))
        if eixo[i] > 1e-12:
            eixo = A[:, i] / eixo[i]
        eixo = eixo / np.linalg.norm(eixo)
        return theta * eixo

    v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return theta * v / (2.0 * np.sin(theta))


def _exp_rot(w):
    """Vetor eixo*ângulo (3,) -> rotação 3x3 (Rodrigues)."""
    theta = np.linalg.norm(w)
    if theta < 1e-12:
        return np.eye(3)
    K = _skew(w / theta)
    return np.eye(3) + np.sin(theta) * K + (1.0 - np.cos(theta)) * (K @ K)


def _movimentos_relativos(T_gripper2base, T_target2cam):
    """Monta os pares (A, B) de movimentos relativos tais que A @ X = X @ B.

    Partindo de T_target2base = T_gripper2base[i] @ X @ T_target2cam[i]
    ser constante, para cada par (i, j):
        A = inv(T_gripper2base[j]) @ T_gripper2base[i]
        B = T_target2cam[j] @ inv(T_target2cam[i])
    """
    pares = []
    n = len(T_gripper2base)

    for i in range(n):
        for j in range(i + 1, n):
            A = np.linalg.inv(T_gripper2base[j]) @ T_gripper2base[i]
            B = T_target2cam[j] @ np.linalg.inv(T_target2cam[i])

            # Pares com rotação relativa quase nula não informam nada sobre a
            # rotação de X e só injetam ruído no sistema.
            if np.linalg.norm(_log_rot(A[:3, :3])) < np.deg2rad(2.0):
                continue
            if np.linalg.norm(_log_rot(B[:3, :3])) < np.deg2rad(2.0):
                continue

            pares.append((A, B))

    return pares


def _rotacao_tsai(pares):
    """Rotação de X pelo método de Tsai & Lenz."""
    S, d = [], []

    for A, B in pares:
        ra, rb = _log_rot(A[:3, :3]), _log_rot(B[:3, :3])
        # Vetor de Rodrigues modificado de Tsai: P = 2*sin(theta/2)*eixo
        ta, tb = np.linalg.norm(ra), np.linalg.norm(rb)
        Pa = 2.0 * np.sin(ta / 2.0) * (ra / ta)
        Pb = 2.0 * np.sin(tb / 2.0) * (rb / tb)

        S.append(_skew(Pa + Pb))
        d.append(Pb - Pa)

    S = np.vstack(S)
    d = np.concatenate(d)

    Px_linha = np.linalg.lstsq(S, d, rcond=None)[0]
    Px = 2.0 * Px_linha / np.sqrt(1.0 + float(Px_linha @ Px_linha))

    n2 = float(Px @ Px)
    return (
        (1.0 - n2 / 2.0) * np.eye(3)
        + 0.5 * (np.outer(Px, Px) + np.sqrt(max(4.0 - n2, 0.0)) * _skew(Px))
    )


def _rotacao_park(pares):
    """Rotação de X pelo método de Park & Martin."""
    M = np.zeros((3, 3))
    for A, B in pares:
        alpha = _log_rot(A[:3, :3])
        beta = _log_rot(B[:3, :3])
        M += np.outer(beta, alpha)

    # Rx = (M^T M)^(-1/2) M^T
    autoval, autovet = np.linalg.eigh(M.T @ M)
    inv_sqrt = autovet @ np.diag(1.0 / np.sqrt(np.maximum(autoval, 1e-12))) @ autovet.T
    R = inv_sqrt @ M.T

    # Reprojeta no grupo das rotações (corrige deriva numérica)
    U, _, Vt = np.linalg.svd(R)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U[:, -1] *= -1
        R = U @ Vt
    return R


def _translacao(pares, Rx):
    """Translação de X, dada a rotação: (Ra - I) tx = Rx @ tb - ta."""
    C, d = [], []
    for A, B in pares:
        C.append(A[:3, :3] - np.eye(3))
        d.append(Rx @ B[:3, 3] - A[:3, 3])

    return np.linalg.lstsq(np.vstack(C), np.concatenate(d), rcond=None)[0]


def calibrate_hand_eye(R_gripper2base, t_gripper2base, R_target2cam, t_target2cam,
                       metodo="TSAI"):
    """Equivalente a cv2.calibrateHandEye. Devolve (R_cam2gripper, t_cam2gripper)."""
    def _montar(Rs, ts):
        saida = []
        for R, t in zip(Rs, ts):
            T = np.eye(4)
            T[:3, :3] = np.asarray(R, dtype=float)
            T[:3, 3] = np.asarray(t, dtype=float).flatten()
            saida.append(T)
        return saida

    pares = _movimentos_relativos(
        _montar(R_gripper2base, t_gripper2base),
        _montar(R_target2cam, t_target2cam),
    )

    if len(pares) < 2:
        raise ValueError(
            "Pares de movimento insuficientes: as poses precisam variar de "
            "orientação (pelo menos 2 graus entre si)."
        )

    metodo = metodo.upper()
    if metodo == "TSAI":
        Rx = _rotacao_tsai(pares)
    elif metodo == "PARK":
        Rx = _rotacao_park(pares)
    else:
        raise ValueError(f"Método não suportado no fallback: {metodo}")

    tx = _translacao(pares, Rx)
    return Rx, tx.reshape(3, 1)
