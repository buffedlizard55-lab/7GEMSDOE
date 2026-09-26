import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import geodawn_extensions as GE


def members(area=2):
    return [
        {"name": f"nested/22103_thk_a{area}.tif", "size": 1},
        {"name": f"nested/22103_uk_a{area}.tif", "size": 1},
        {"name": f"nested/22103_uth_a{area}.tif", "size": 1},
        {"name": f"nested/22103_upcont_tmi150_a{area}.tif", "size": 1},
        {"name": f"nested/22103_k_a{area}.tif", "size": 1},
    ]


def test_selects_exact_observed_extension_members():
    selected = GE.select_extension_members(members(), 2)
    assert list(selected) == list(GE.CHANNELS)
    assert selected["ThK"]["name"].endswith("22103_thk_a2.tif")
    assert selected["TMI_up150"]["name"].endswith("22103_upcont_tmi150_a2.tif")


def test_selection_is_case_insensitive_but_not_substring_based():
    observed = members(1)
    observed[0]["name"] = "X/22103_THK_A1.TIF"
    assert GE.select_extension_members(observed, 1)["ThK"]["name"].endswith("TIF")
    observed[0]["name"] = "X/copy_22103_thk_a1.tif"
    with pytest.raises(ValueError, match="expected one exact"):
        GE.select_extension_members(observed, 1)


def test_missing_duplicate_and_unknown_area_fail_closed():
    with pytest.raises(ValueError, match="found 0"):
        GE.select_extension_members(members()[:-2], 2)
    duplicate = members() + [{"name": "other/22103_uk_a2.tif", "size": 2}]
    with pytest.raises(ValueError, match="found 2"):
        GE.select_extension_members(duplicate, 2)
    with pytest.raises(ValueError, match="unsupported"):
        GE.select_extension_members(members(), 3)
