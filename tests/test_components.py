"""Tests for components.py — union-find connected component analysis."""

import pytest
from diagram_sanitizer.grid import Grid, classify_connectors
from diagram_sanitizer.components import (
    find_components,
    UnionFind,
    Component,
)


class TestUnionFind:

    def test_initial_state(self):
        uf = UnionFind(5)
        for i in range(5):
            assert uf.find(i) == i

    def test_union_two(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        assert uf.find(0) == uf.find(1)
        assert uf.find(0) != uf.find(2)

    def test_union_transitive(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        uf.union(1, 2)
        assert uf.find(0) == uf.find(2)

    def test_union_idempotent(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        uf.union(0, 1)
        assert uf.find(0) == uf.find(1)

    def test_path_compression(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        uf.union(1, 2)
        uf.union(2, 3)
        uf.union(3, 4)
        # All should share the same root
        root = uf.find(0)
        for i in range(5):
            assert uf.find(i) == root


class TestConnectedComponents:

    def test_simple_box_is_one_component(self):
        grid = Grid("┌─┐\n│ │\n└─┘")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        assert len(components) == 1
        assert components[0].size == 8

    def test_two_separate_boxes_two_components(self):
        grid = Grid("┌─┐  ┌─┐\n└─┘  └─┘")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        assert len(components) == 2

    def test_disconnected_line_endpoints_one_component(self):
        # Even though the hbar has no junctions, the two ── form one component
        # because they are directly connected (each expects left/right)
        grid = Grid("──")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        assert len(components) == 1
        assert components[0].size == 2

    def test_component_cells_are_correct(self):
        grid = Grid("┌┐\n└┘")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        assert len(components) == 1
        chars = {c.char for c in components[0].cells}
        assert chars == {"┌", "┐", "└", "┘"}

    def test_cross_connects_all_four_arms(self):
        grid = Grid(" │\n─┼─\n │")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        assert len(components) == 1
        assert components[0].size >= 5  # ┼, ─, ─, │, │

    def test_adjacent_but_not_connected(self):
        # ─ next to │ — adjacent but neither expects connection toward the other
        # │ doesn't expect RIGHT, and │ doesn't expect LEFT from ─'s perspective
        grid = Grid(" │─")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        # │ and ─ should be in separate components
        assert len(components) == 2

    def test_diagonal_characters_connected(self):
        grid = Grid("╲\n ╲")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        # Diagonals connect via Chebyshev distance 1
        assert len(components) == 1
        assert components[0].size == 2

    def test_empty_connectors_list(self):
        grid = Grid("abc")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        assert components == []

    def test_nested_boxes_separate_components(self):
        grid = Grid("┌───────┐\n│ ┌───┐ │\n│ └───┘ │\n└───────┘")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        assert len(components) == 2
        # Outer box should be larger
        assert components[0].size > components[1].size

    def test_ascii_box_one_component(self):
        grid = Grid("+---+\n| A |\n+---+")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        # + (loose) connects to - and |, which connect to each other and back to +
        assert len(components) == 1

    def test_components_sorted_by_size(self):
        grid = Grid("┌───────────┐\n└───────────┘\n\n┌─┐\n└─┘")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        assert len(components) >= 2
        # Largest first
        assert components[0].size > components[1].size

    def test_component_dataclass_fields(self):
        grid = Grid("──")
        connectors = classify_connectors(grid)
        components = find_components(connectors, grid)
        comp = components[0]
        assert isinstance(comp, Component)
        assert comp.size == 2
        assert len(comp.cells) == 2
        assert isinstance(comp.id, int)
