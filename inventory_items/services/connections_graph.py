# services/connections_graph.py

class ConnectionsGraph:
    """
    Built once at StateStore init from the rooms list.
    Resolves room names to IDs and encodes all movement rules.

    Rules:
      - A room with movement_group can reach all rooms sharing that group.
      - A room can reach any connectoid whose connections list includes its name.
      - A connectoid can only reach the rooms listed in its connections.
      - A room with no movement_group and not a connectoid is isolated —
        it never appears in any accessible set unless a connectoid lists it.
    """

    def __init__(self, rooms: list[dict]):
        # name → id
        self._name_to_id: dict[str, int] = {}
        # id → movement_group (str | None)
        self._group: dict[int, str | None] = {}
        # group → set of room IDs
        self._group_members: dict[str, set[int]] = {}
        # connectoid id → list of connected room IDs
        self._connectoid_connections: dict[int, list[int]] = {}
        # room id → list of connectoid IDs that list this room
        self._room_exits: dict[int, list[int]] = {}

        self._build(rooms)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, rooms: list[dict]) -> None:
        # First pass: index all rooms by name and collect group membership
        for room in rooms:
            if not isinstance(room, dict):
                continue
            room_id = room.get("id")
            name = room.get("name")
            if not isinstance(room_id, int) or not isinstance(name, str):
                continue

            self._name_to_id[name.lower()] = room_id
            group = room.get("movement_group")  # str or None
            self._group[room_id] = group

            if isinstance(group, str) and group:
                self._group_members.setdefault(group, set()).add(room_id)

        # Second pass: resolve connectoids (needs name_to_id complete)
        validation_errors = []
        for room in rooms:
            if not isinstance(room, dict):
                continue
            if not room.get("is_connectoid", False):
                continue

            room_id = room.get("id")
            raw_connections = room.get("connections", [])

            resolved_ids = []
            for conn_name in raw_connections:
                if not isinstance(conn_name, str):
                    validation_errors.append(
                        f"Connectoid '{room.get('name')}' has non-string connection entry: {conn_name!r}"
                    )
                    continue
                target_id = self._name_to_id.get(conn_name.lower())
                if target_id is None:
                    validation_errors.append(
                        f"Connectoid '{room.get('name')}' references unknown room '{conn_name}'."
                    )
                    continue
                resolved_ids.append(target_id)

            self._connectoid_connections[room_id] = resolved_ids

            # Register this connectoid as an exit for each of its connected rooms
            for target_id in resolved_ids:
                self._room_exits.setdefault(target_id, []).append(room_id)

        if validation_errors:
            for err in validation_errors:
                print(f"[ConnectionsGraph] Validation Warning: {err}")

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def get_accessible_ids(self, current_room_id: int) -> list[int]:
        """
        Returns all room IDs accessible from current_room_id,
        excluding the current room itself.
        """
        accessible: set[int] = set()

        if current_room_id in self._connectoid_connections:
            # Current room IS a connectoid — can only reach its declared connections
            for target_id in self._connectoid_connections[current_room_id]:
                if target_id != current_room_id:
                    accessible.add(target_id)
        else:
            # Regular room (or isolated room with no group)
            group = self._group.get(current_room_id)
            if isinstance(group, str) and group:
                # All group members except self
                for member_id in self._group_members.get(group, set()):
                    if member_id != current_room_id:
                        accessible.add(member_id)

            # Any connectoids whose connections list includes this room
            for connectoid_id in self._room_exits.get(current_room_id, []):
                accessible.add(connectoid_id)

        return list(accessible)

    def is_accessible(self, current_room_id: int, target_room_id: int) -> bool:
        return target_room_id in self.get_accessible_ids(current_room_id)