import numpy as np
import qpsolvers as qp
import roboticstoolbox as rtb
import spatialgeometry as sg
import swift

QP_SOLVER = "quadprog" if "quadprog" in qp.available_solvers else "osqp"

def step_robot(robot: rtb.ERobot, T_b: np.ndarray) -> tuple[bool, np.ndarray]:
    alpha = 0.5
    beta = 2.0
    slack = 10.0
    arrival_eps = 0.02

    T_a = robot.fkine(robot.q).A
    eTep = np.linalg.inv(T_a) @ T_b
    et = max(float(np.sum(np.abs(eTep[:3, 3]))), 1e-6)

    Q = np.eye(robot.n + 6)
    Q[: robot.n, : robot.n] *= 0.01
    Q[robot.n :, robot.n :] *= 1.0 / et

    v, _ = rtb.p_servo(T_a, T_b, beta)

    Aeq = np.c_[robot.jacobe(robot.q), np.eye(6)]
    beq = v.reshape(6)

    c = np.zeros(robot.n + 6)
    c[: robot.n] = alpha * gmrm_xz_grad(robot, robot.q)

    lb = -np.r_[robot.qdlim[: robot.n], slack * np.ones(6)]
    ub = np.r_[robot.qdlim[: robot.n], slack * np.ones(6)]

    x = qp.solve_qp(Q, c, A=Aeq, b=beq, lb=lb, ub=ub, solver=QP_SOLVER)
    if x is None:
        return False, np.zeros(robot.n)

    qd = x[: robot.n]

    print(f"et={et:.4f}, gmrm_xz={gmrm_xz(robot, robot.q):.4f}")
    return et < arrival_eps, qd


env = swift.Swift()
env.launch(realtime=True)

ax_goal = sg.Axes(0.1)
env.add(ax_goal)

panda = rtb.models.URDF.Panda()
panda.q = panda.qr
env.add(panda)

T_B = panda.fkine(panda.q).A
T_B[:3, 3] += np.array([0.3, 0.0, -0.20])
ax_goal.T = T_B

env.set_camera_pose([2.2, 2.0, 1.4], [0.4, 0.0, 0.4])
env.step()

dt = 0.025
for _ in range(2000):
    arrived, panda.qd = step_robot(panda, T_B)
    env.step(dt)
    if arrived:
        break

env.hold()
