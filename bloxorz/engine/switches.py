# Phụ trách: VT2 - Task 2.3
"""
Cơ chế công tắc mềm (soft switch), công tắc nặng (heavy switch) và cầu đóng/mở (bridges).

Quy tắc theo Section 2.5 của đồ án:
- Soft switch (hình tròn/bát giác): Kích hoạt khi bất kỳ phần nào của khối đè lên nó (nằm hoặc đứng).
- Heavy switch (chữ X): Chỉ kích hoạt khi khối ở tư thế ĐỨNG THẲNG (standing) trên ô công tắc.
  Khi khối nằm (horizontal/vertical) đè qua ô công tắc nặng thì không kích hoạt.
- Split switch (hình ngoặc ( )): Thuộc Task 2.4, chỉ kích hoạt khi đứng và do split.py xử lý.
- Khi được kích hoạt, công tắc tác động lên các cây cầu liên kết theo:
  * "toggle": đảo trạng thái giữa mở (open) và đóng (closed).
  * "open": mở cầu (cho phép khối đi qua như sàn thường).
  * "close": đóng cầu (trở thành khoảng trống/void khiến khối rơi nếu bước lên).
"""

from __future__ import annotations
from typing import Sequence

from bloxorz.model import Pose, Pos
from bloxorz.stage import BridgeAction, Stage, Switch


def can_activate_switch(switch: Switch, pose: Pose | None) -> bool:
    """
    Kiểm tra xem với tư thế pose hiện tại, khối có đủ điều kiện kích hoạt switch hay không.
    - soft switch: luôn kích hoạt khi chạm vào (cả đứng, nằm ngang, nằm dọc, hoặc cube 1x1).
    - heavy switch: chỉ kích hoạt khi khối đứng thẳng (Pose.STANDING).
    - split switch: chỉ kích hoạt khi khối đứng thẳng (Pose.STANDING).
    """
    if switch.kind == "soft":
        return True
    if switch.kind == "heavy":
        return pose == Pose.STANDING
    if switch.kind == "split":
        return pose == Pose.STANDING
    return False


def apply_bridge_action(bridges_open: frozenset[str], bridge_id: str, action: BridgeAction) -> frozenset[str]:
    """
    Áp dụng một hành động ("toggle" | "open" | "close") lên một cây cầu cụ thể.
    Trả về tập hợp bridges_open mới (bất biến - frozenset).
    """
    current = set(bridges_open)
    if action == "toggle":
        if bridge_id in current:
            current.remove(bridge_id)
        else:
            current.add(bridge_id)
    elif action == "open":
        current.add(bridge_id)
    elif action == "close":
        current.discard(bridge_id)
    else:
        raise ValueError(f"Hành động cầu không hợp lệ: {action}")
    return frozenset(current)


def apply_switch(switch: Switch, bridges_open: frozenset[str]) -> frozenset[str]:
    """
    Áp dụng toàn bộ actions của một công tắc lên tập hợp cầu đang mở bridges_open.
    Trả về tập hợp bridges_open mới.
    """
    if switch.kind == "split" or not switch.actions:
        return bridges_open

    current = set(bridges_open)
    for bridge_id, action in switch.actions:
        if action == "toggle":
            if bridge_id in current:
                current.remove(bridge_id)
            else:
                current.add(bridge_id)
        elif action == "open":
            current.add(bridge_id)
        elif action == "close":
            current.discard(bridge_id)
        else:
            raise ValueError(f"Hành động cầu không hợp lệ: {action}")

    return frozenset(current)


def trigger_switches(
    stage: Stage,
    pose: Pose | None,
    cells: Sequence[Pos],
    bridges_open: frozenset[str],
) -> frozenset[str]:
    """
    Kiểm tra và kích hoạt các công tắc nằm tại các ô cells mà khối tiếp đất.
    - stage: bản đồ màn chơi chứa stage.switch_at.
    - pose: tư thế khối sau khi lăn.
    - cells: danh sách tọa độ các ô mà khối đang chiếm giữ.
    - bridges_open: tập các id cầu đang mở trước khi kích hoạt.
    Trả về tập hợp bridges_open mới sau khi tất cả công tắc hợp lệ được kích hoạt.
    """
    # Không có công tắc nào trong màn -> giữ nguyên
    if not stage.switches:
        return bridges_open

    switch_mapping = stage.switch_at
    updated_bridges = bridges_open

    # Duyệt qua các ô của khối theo thứ tự tọa độ tăng dần để đảm bảo tính tất định (deterministic)
    for p in sorted(cells):
        sw = switch_mapping.get(p)
        if sw is not None and sw.kind != "split" and can_activate_switch(sw, pose):
            updated_bridges = apply_switch(sw, updated_bridges)

    return updated_bridges
