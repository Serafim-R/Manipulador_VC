"""
Ajuda a escolher a POSICAO_BUSCA (pose fixa de observacao).

Dada uma pose candidata, projeta os cantos da imagem sobre o plano da mesa e
mostra que retangulo a camera enxerga dali, em coordenadas de MUNDO (as
mesmas que robot_control.mover_para() recebe).

Uso:
    python ferramentas/checar_pose_busca.py
    python ferramentas/checar_pose_busca.py -300 210 400
"""

import os
import sys
import types

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# gpiozero so existe no Pi com as libs instaladas; aqui nada toca o hardware
if "gpiozero" not in sys.modules:
    try:
        import gpiozero  # noqa: F401
    except ImportError:
        _stub = types.ModuleType("gpiozero")
        _stub.OutputDevice = object
        sys.modules["gpiozero"] = _stub

import robot_control                                      # noqa: E402
from backend.calibration.vision_to_robot import VisionToRobot   # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(RAIZ, "backend", "calibration", "dados")

LARGURA, ALTURA = 640, 480      # resolucao da camera (camera_manager.py)
Z_MESA_MUNDO = 0.0              # igual ao app_controller


class _SerialMudo:
    def send(self, msg):
        pass


class _UnityMudo:
    def send_angles(self, *a, **k):
        pass


def pose_de_observacao(x, y, z):
    """T_flange_base da pose candidata, pelo mesmo caminho que o robo usa."""
    robot_control.time.sleep = lambda *a, **k: None

    robo = robot_control.RobotController(_SerialMudo(), _UnityMudo())
    robo.mover_para(float(x), float(y), float(z))

    return robo.pose_flange_atual()


def main():
    alvo = sys.argv[1:4]
    x, y, z = (float(v) for v in alvo) if len(alvo) == 3 else (-300.0, 210.0, 400.0)

    v2r = VisionToRobot(
        os.path.join(DADOS, "calibracao_intrinseca.npz"),
        os.path.join(DADOS, "calibracao_mao_olho.npz"),
    )

    T_flange_base = pose_de_observacao(x, y, z)

    print(f"Pose de observacao (mundo, ponta): X={x:.1f} Y={y:.1f} Z={z:.1f}")
    print(f"Flange na base: {T_flange_base[:3, 3].round(1)}")
    print(f"Eixo optico (Z da camera, na base): "
          f"{(T_flange_base[:3, :3] @ v2r.T_cam_flange[:3, :3])[:, 2].round(3)}")
    print(f"\nPlano da mesa: z = {Z_MESA_MUNDO:.1f} mm (mundo)\n")

    cantos = {
        "sup-esq": (0, 0),
        "sup-dir": (LARGURA - 1, 0),
        "inf-esq": (0, ALTURA - 1),
        "inf-dir": (LARGURA - 1, ALTURA - 1),
        "centro ": (LARGURA / 2, ALTURA / 2),
    }

    pontos = {}
    for nome, (u, v) in cantos.items():
        try:
            pontos[nome] = v2r.deteccao_para_mundo(
                (u, v, u, v), T_flange_base, z_plano_mundo=Z_MESA_MUNDO
            )
        except ValueError as erro:
            print(f"  {nome}: FORA DO PLANO -> {erro}")

    if len(pontos) < len(cantos):
        print("\nEsta pose nao serve: parte da imagem nao cruza a mesa.")
        return 1

    print("Onde cada ponto da imagem cai na mesa (mundo, mm):")
    for nome, p in pontos.items():
        print(f"  {nome}: X={p[0]:8.1f}  Y={p[1]:8.1f}")

    xs = [p[0] for p in pontos.values()]
    ys = [p[1] for p in pontos.values()]
    print(f"\nRegiao visivel: X de {min(xs):.0f} a {max(xs):.0f} mm "
          f"({max(xs) - min(xs):.0f} mm de largura)")
    print(f"                Y de {min(ys):.0f} a {max(ys):.0f} mm "
          f"({max(ys) - min(ys):.0f} mm de altura)")

    # Quantos mm vale 1 pixel no centro: da a precisao esperada da conversao
    centro = pontos["centro "]
    vizinho = v2r.deteccao_para_mundo(
        (LARGURA / 2 + 1, ALTURA / 2, LARGURA / 2 + 1, ALTURA / 2),
        T_flange_base, z_plano_mundo=Z_MESA_MUNDO,
    )
    mm_por_pixel = float(np.linalg.norm(vizinho - centro))
    print(f"\nEscala no centro: {mm_por_pixel:.2f} mm por pixel")
    print(f"  -> um erro de 5 px na CNN vira ~{5 * mm_por_pixel:.1f} mm na mesa")

    return 0


if __name__ == "__main__":
    sys.exit(main())
