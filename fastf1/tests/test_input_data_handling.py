# test some known special cases

import pytest

import logging

import pandas as pd

import fastf1
import fastf1.ergast
import fastf1.testing
from fastf1.testing.reference_values import LAP_DTYPES


@pytest.mark.f1telapi
@pytest.mark.skip(reason="required data not available")
def test_partial_position_data(caplog):
    # RUS is missing the first half of the position data because F1 somehow
    # switches from development driver to RUS mid-session
    # this requires recreating missing data (empty) so that the data has the correct size
    caplog.set_level(logging.INFO)

    session = fastf1.get_session(2020, 'Barcelona', 'FP2')
    session.load()

    assert "Car data for driver 63 is incomplete!" in caplog.text  # the warning
    assert "Laps loaded and saved!" in caplog.text  # indicates success


@pytest.mark.f1telapi
@pytest.mark.skip(reason="required data not available")
def test_history_mod_1(caplog):
    # api data sometimes goes back in time
    caplog.set_level(logging.INFO)

    session = fastf1.get_session(2020, 'testing', 3)
    session.load()

    assert "The api attempted to rewrite history" in caplog.text  # the warning
    assert "Laps loaded and saved!" in caplog.text  # indicates success


@pytest.mark.f1telapi
def test_ergast_lookup_fail():
    fastf1.testing.run_in_subprocess(_test_ergast_lookup_fail)


def _test_ergast_lookup_fail():
    fastf1.Cache.enable_cache('test_cache')
    log_handle = fastf1.testing.capture_log()

    # ergast lookup fails if data is requested to soon after a session ends

    def fail_load(*args, **kwargs):
        raise Exception
    fastf1.ergast.fetch_results = fail_load  # force function call to fail

    session = fastf1.get_session(2020, 3, 'FP2')  # rainy and short session, good for fast test/quick loading
    session.load(telemetry=False, weather=False)

    assert "Failed to load data from Ergast API!" in log_handle.text  # the warning
    assert "Finished loading data" in log_handle.text  # indicates success


@pytest.mark.f1telapi
def test_crash_lap_added_1():
    # sainz crashed in his 14th lap, there need to be all 14 laps
    session = fastf1.get_session(2021, "Monza", 'FP2')

    session.load(telemetry=False)
    assert session.laps.pick_driver('SAI').shape[0] == 14


@pytest.mark.f1telapi
def test_crash_lap_added_2():
    # verstappen crashed on his first lap, the lap needs to exist
    session = fastf1.get_session(2021, 'British Grand Prix', 'R')

    session.load(telemetry=False)
    assert session.laps.pick_driver('VER').shape[0] == 1


@pytest.mark.f1telapi
def test_no_extra_lap_if_race_not_started():
    # tsunoda had a technical issue shortly before the race and could not
    # start even though he is listed in the drivers list
    session = fastf1.get_session(2022, 2, 'R')

    session.load(telemetry=False, weather=False)
    assert session.laps.size
    assert session.laps.pick_driver('TSU').size == 0


@pytest.mark.f1telapi
def test_no_timing_app_data():
    fastf1.testing.run_in_subprocess(_test_no_timing_app_data)


def _test_no_timing_app_data():
    # subprocess test because api parser function is overwritten
    log_handle = fastf1.testing.capture_log(logging.WARNING)

    def _mock(*args, **kwargs):
        return pd.DataFrame(
            {'LapNumber': [], 'Driver': [], 'LapTime': [], 'Stint': [],
             'TotalLaps': [], 'Compound': [], 'New': [],
             'TyresNotChanged': [], 'Time': [], 'LapFlags': [],
             'LapCountTime': [], 'StartLaps': [], 'Outlap': []}
        )

    fastf1.api.timing_app_data = _mock

    session = fastf1.get_session(2020, 'Italy', 'R')
    with fastf1.Cache.disabled():
        session.load(telemetry=False, weather=False)

    assert 'Failed to load lap data!' not in log_handle.text
    assert 'No tyre data for driver' in log_handle.text

    assert session.laps.size
    assert all([col in session.laps.columns for col in LAP_DTYPES.keys()])


@pytest.mark.f1telapi
def test_inlap_added():
    session = fastf1.get_session(2021, 'Mexico City', 'Q')

    with fastf1.Cache.disabled():
        session.load(telemetry=False)

    last = session.laps.pick_driver('PER').iloc[-1]
    assert not pd.isnull(last['PitInTime'])
    assert not pd.isnull(last['Time'])
