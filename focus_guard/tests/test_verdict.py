# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
from datetime import date, timedelta

from focus_project import Limits, Project

from focus_guard._constants import JUDGE_FROM
from focus_guard._verdict import decide, local_today
from focus_guard.tests._days import DAY
from focus_guard.tests.conftest import World, project

YESTERDAY = DAY - timedelta(days=1)


def test_short_yesterday_locks_with_the_numbers(world: World) -> None:
    world.short_yesterday().minutes[DAY] = 5
    verdict = decide(DAY)
    assert verdict.locked
    assert (verdict.name, verdict.today_minutes, verdict.unlock_minutes) == (
        "Exam",
        5,
        30,
    )
    assert (verdict.yesterday_minutes, verdict.daily_minutes) == (10, 120)


def test_met_yesterday_does_not_lock(world: World) -> None:
    world.minutes[YESTERDAY] = 120
    verdict = decide(DAY)
    assert not verdict.locked
    assert verdict.reason == "yesterday kept its number"


def test_unlock_minutes_today_lift_the_lock(world: World) -> None:
    world.short_yesterday().minutes[DAY] = 30
    verdict = decide(DAY)
    assert not verdict.locked
    assert verdict.today_minutes == 30
    assert verdict.reason == "today's minutes are in"


def test_below_unlock_by_one_still_locks(world: World) -> None:
    world.short_yesterday().minutes[DAY] = 29
    assert decide(DAY).locked


def test_no_project_today(world: World) -> None:
    world.projects = [project(end=YESTERDAY)]
    assert decide(DAY).reason == "no project today"


def test_yesterday_was_not_a_project_day(world: World) -> None:
    world.projects = [project(start=DAY)]
    assert decide(DAY).reason == "yesterday was not a project day"


def test_sick_today_never_locks(world: World) -> None:
    world.short_yesterday().sick.add(DAY)
    assert decide(DAY).reason == "today is a sick or free day"


def test_free_today_never_locks(world: World) -> None:
    world.short_yesterday().free.add(DAY)
    assert not decide(DAY).locked


def test_sick_yesterday_owes_nothing(world: World) -> None:
    world.sick.add(YESTERDAY)
    assert decide(DAY).reason == "yesterday kept its number"


def test_a_sick_day_that_keeps_focus_still_locks(world: World) -> None:
    world.short_yesterday().sick.add(DAY)
    world.kept.add(DAY)
    assert decide(DAY).locked


def test_a_sick_yesterday_that_kept_focus_still_owes(world: World) -> None:
    world.sick.add(YESTERDAY)
    world.kept.add(YESTERDAY)
    assert decide(DAY).reason == "yesterday fell short"


def test_free_yesterday_owes_nothing(world: World) -> None:
    world.free.add(YESTERDAY)
    assert not decide(DAY).locked


def test_nothing_before_the_first_judged_day(world: World) -> None:
    world.short_yesterday()
    assert not decide(JUDGE_FROM).locked
    assert decide(JUDGE_FROM + timedelta(days=1)).locked


def test_local_today_is_a_date() -> None:
    assert isinstance(local_today(), date)


def _edited(old: tuple[int, int], new: tuple[int, int]) -> Project:
    """A project edited today: the ``old`` (daily, unlock) held through yesterday."""
    limits = Limits(until=YESTERDAY, daily_minutes=old[0], unlock_minutes=old[1])
    return project(history=(limits,), daily=new[0], unlock=new[1])


def test_a_lowered_daily_is_not_applied_back_to_yesterday(world: World) -> None:
    world.projects = [_edited(old=(120, 30), new=(60, 30))]
    world.minutes[YESTERDAY] = 100
    verdict = decide(DAY)
    assert verdict.locked
    assert verdict.daily_minutes == 120


def test_a_raised_daily_does_not_re_judge_yesterday(world: World) -> None:
    world.projects = [_edited(old=(60, 30), new=(200, 30))]
    world.minutes[YESTERDAY] = 70
    assert decide(DAY).reason == "yesterday kept its number"


def test_todays_unlock_is_the_edited_one(world: World) -> None:
    world.projects = [_edited(old=(120, 30), new=(120, 10))]
    world.short_yesterday().minutes[DAY] = 5
    verdict = decide(DAY)
    assert verdict.locked
    assert verdict.unlock_minutes == 10
    world.minutes[DAY] = 10
    assert not decide(DAY).locked


def test_an_old_edit_row_does_not_touch_later_days(world: World) -> None:
    long_ago = Limits(
        until=YESTERDAY - timedelta(days=5), daily_minutes=1, unlock_minutes=1
    )
    world.projects = [project(history=(long_ago,))]
    world.short_yesterday()
    verdict = decide(DAY)
    assert (verdict.daily_minutes, verdict.unlock_minutes) == (120, 30)
