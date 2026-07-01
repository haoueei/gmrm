import numpy as np
import qpsolvers as qp
import roboticstoolbox as rtb
import spatialgeometry as sg
import swift

QP_SOLVER = "quadprog" if "quadprog" in qp.available_solvers else "osqp"
EPS = 1e-9
XZ_BASIS = np.array([[1.0, 0.0], [0.0, 0.0], [0.0, 1.0]])


def translational_lambda_inv(robot, q):
    Jv = np.asarray(robot.jacob0(q), dtype=float)[:3]
    M = np.asarray(robot.inertia(q), dtype=float)
    return Jv @ np.linalg.solve(M, Jv.T)


def restricted_eigvals(Av, B0=None):
    B0 = np.eye(3) if B0 is None else np.asarray(B0, dtype=float)
    A0 = B0.T @ np.asarray(Av, dtype=float) @ B0
    return np.linalg.eigvalsh((A0 + A0.T) / 2.0)


def hard_rank_from_av(Av, B0=None, eps=EPS):
    return int(np.count_nonzero(restricted_eigvals(Av, B0) > eps))


def gmrm_from_av(Av, B0=None, eps=EPS):
    sigma = restricted_eigvals(Av, B0)
    width = eps * 0.1
    # Smooth floor avoids discrete rank drops when an eigenvalue crosses eps.
    sigma = eps + width * np.logaddexp(0.0, (sigma - eps) / width)
    lambdas = 1.0 / sigma

    if lambdas.size == 1:
        return float(lambdas[0])
    if lambdas.size == 2:
        return float(np.sqrt(lambdas[0] * lambdas[1]))
    if lambdas.size == 3:
        return mean_reflected_mass(
            np.sqrt(lambdas[0]), np.sqrt(lambdas[1]), np.sqrt(lambdas[2])
        )

    raise ValueError("no positive translational modes in the candidate subspace")


def mean_reflected_mass(a, b, c, n=200):
    lambdas = np.linspace(0, np.pi / 2, n)
    gammas = np.linspace(0, np.pi / 2, n)
    L, G = np.meshgrid(lambdas, gammas)
    r = (a * b * c) / np.sqrt(
        c**2 * (b**2 * np.cos(L) ** 2 + a**2 * np.sin(L) ** 2) * np.cos(G) ** 2
        + a**2 * b**2 * np.sin(G) ** 2
    )
    return float(
        (2 / np.pi) * np.trapezoid(np.trapezoid(r**2 * np.cos(G), L[0]), G[:, 0])
    )


def gmrm(robot, q, B0=XZ_BASIS):
    return gmrm_from_av(translational_lambda_inv(robot, q), B0)


def gmrm_grad(robot, q, B0=XZ_BASIS):
    h = 1e-4
    grad = np.zeros_like(q)

    for i in range(q.size):
        dq = np.zeros_like(q)
        dq[i] = h
        grad[i] = (gmrm(robot, q + dq, B0) - gmrm(robot, q - dq, B0)) / (2.0 * h)

    return grad


def step_robot(robot, Tep):
    gmrm_gain = 0.2
    servo_gain = 2.0
    slack_limit = 10.0
    arrived_tol = 0.02

    Te = robot.fkine(robot.q).A
    eTep = np.linalg.inv(Te) @ Tep
    et = max(float(np.sum(np.abs(eTep[:3, 3]))), 1e-6)

    Q = np.eye(robot.n + 6)
    Q[: robot.n, : robot.n] *= 0.01
    Q[robot.n :, robot.n :] *= 1.0 / et

    v, _ = rtb.p_servo(Te, Tep, servo_gain)

    Aeq = np.c_[robot.jacobe(robot.q), np.eye(6)]
    beq = v.reshape(6)

    c = np.zeros(robot.n + 6)
    c[: robot.n] = gmrm_gain * gmrm_grad(robot, robot.q)

    lb = -np.r_[robot.qdlim[: robot.n], slack_limit * np.ones(6)]
    ub = np.r_[robot.qdlim[: robot.n], slack_limit * np.ones(6)]

    x = qp.solve_qp(Q, c, A=Aeq, b=beq, lb=lb, ub=ub, solver=QP_SOLVER)
    qd = np.zeros(robot.n) if x is None else x[: robot.n]

    Av = translational_lambda_inv(robot, robot.q)
    return (
        et < arrived_tol,
        qd,
        et,
        gmrm_from_av(Av, XZ_BASIS),
        hard_rank_from_av(Av, XZ_BASIS),
    )


def _self_check():
    assert np.isclose(
        gmrm_from_av(np.diag([0.25, 1.0 / 9.0, 0.0]), np.eye(3)[:, :2]), 6.0
    )
    rank_limited = gmrm_from_av(np.diag([0.25, 0.0, 0.0]), np.eye(3)[:, :2])
    assert np.isfinite(rank_limited) and rank_limited > 4.0
    assert hard_rank_from_av(np.diag([0.25, 0.0, 0.0]), np.eye(3)[:, :2]) == 1
    assert np.isclose(
        gmrm_from_av(np.diag([0.25, 1.0 / 9.0, 1.0 / 16.0]), XZ_BASIS), 8.0
    )


_self_check()

env = swift.Swift()
env.launch(realtime=True)

ax_goal = sg.Axes(0.1)
env.add(ax_goal)

panda = rtb.models.URDF.Panda()
panda.q = panda.qr
env.add(panda)

Tep = panda.fkine(panda.q).A
Tep[:3, 3] += np.array([0.1, -0.3, -0.25])
ax_goal.T = Tep

env.set_camera_pose([1, -1, 1.4], [0.4, 0.0, 0.4])

dt = 0.025
for _ in range(10):
    env.step(dt)

last_rank = None
for i in range(2000):
    arrived, panda.qd, et, measure, rank = step_robot(panda, Tep)
    env.step(dt)

    rank_changed = rank != last_rank
    if i % 25 == 0 or arrived or rank_changed:
        print(f"step={i:04d}, et={et:.4f}, gmrm_xz={measure:.4f}, rank_xz={rank}")
    last_rank = rank

    if arrived:
        break

env.hold()
