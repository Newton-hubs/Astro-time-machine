"""
Unit tests for AstronomyService.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.astronomy_service import AstronomyService


@pytest.fixture
def service():
    return AstronomyService()


@pytest.fixture
def sample_dt():
    return datetime(2024, 7, 4, 21, 0, 0, tzinfo=timezone.utc)


class TestMoonPhaseNames:
    def test_new_moon(self, service):
        assert service._moon_phase_name(0) == "New Moon"
        assert service._moon_phase_name(355) == "New Moon"

    def test_full_moon(self, service):
        assert service._moon_phase_name(180) == "Full Moon"

    def test_first_quarter(self, service):
        assert service._moon_phase_name(90) == "First Quarter"

    def test_last_quarter(self, service):
        assert service._moon_phase_name(270) == "Last Quarter"

    def test_waxing_crescent(self, service):
        assert service._moon_phase_name(45) == "Waxing Crescent"

    def test_waning_gibbous(self, service):
        assert service._moon_phase_name(225) == "Waning Gibbous"

    def test_all_phases_covered(self, service):
        """Every degree 0-359 should map to a valid phase."""
        valid_phases = {
            "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
            "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent",
        }
        for deg in range(360):
            phase = service._moon_phase_name(float(deg))
            assert phase in valid_phases, f"Unexpected phase '{phase}' for {deg}°"


class TestComputeMoon:
    @patch.object(AstronomyService, "_load_ephemeris")
    def test_returns_moon_data(self, mock_load, service, sample_dt):
        """compute_moon should return a MoonData object with correct types."""
        # Build a minimal mock ephemeris
        ts_mock = MagicMock()
        eph_mock = MagicMock()

        t_mock = MagicMock()
        ts_mock.from_datetime.return_value = t_mock

        alt_mock = MagicMock()
        alt_mock.degrees = 42.5
        az_mock = MagicMock()
        az_mock.degrees = 180.0
        dist_mock = MagicMock()

        apparent_mock = MagicMock()
        apparent_mock.altaz.return_value = (alt_mock, az_mock, dist_mock)

        separation_mock = MagicMock()
        separation_mock.degrees = 130.0  # ~waxing gibbous elongation

        observe_chain = MagicMock()
        observe_chain.observe.return_value.apparent.return_value = apparent_mock
        observe_chain.observe.return_value.separation_from.return_value = separation_mock

        eph_mock.__getitem__ = MagicMock(return_value=MagicMock())

        earth_mock = MagicMock()
        earth_mock.__add__ = MagicMock(return_value=earth_mock)
        earth_mock.at.return_value = observe_chain

        def eph_getitem(key):
            return earth_mock

        eph_mock.__getitem__.side_effect = eph_getitem
        mock_load.return_value = (ts_mock, eph_mock)

        moon_data = service.compute_moon(12.97, 77.59, sample_dt, cloud_cover_pct=0.0)

        assert moon_data.phase_name in {
            "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
            "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent",
        }
        assert 0 <= moon_data.illumination_pct <= 100
        assert isinstance(moon_data.is_above_horizon, bool)
        assert isinstance(moon_data.is_cloud_obscured, bool)

    def test_cloud_obscured_when_above_horizon_and_high_clouds(self, service, sample_dt):
        """Moon above horizon + >70% cloud cover => is_cloud_obscured = True."""
        with patch.object(AstronomyService, "_load_ephemeris") as mock_load:
            ts_mock = MagicMock()
            eph_mock = MagicMock()
            t_mock = MagicMock()
            ts_mock.from_datetime.return_value = t_mock

            alt_mock = MagicMock() 
            alt_mock.degrees = 30.0
            az_mock = MagicMock() 
            az_mock.degrees = 90.0
            dist_mock = MagicMock()
            sep_mock = MagicMock() 
            sep_mock.degrees = 180.0

            apparent = MagicMock()
            apparent.altaz.return_value = (alt_mock, az_mock, dist_mock)

            observe = MagicMock()
            observe.observe.return_value.apparent.return_value = apparent
            observe.observe.return_value.separation_from.return_value = sep_mock

            earth = MagicMock()
            earth.__add__ = MagicMock(return_value=earth)
            earth.at.return_value = observe
            eph_mock.__getitem__ = MagicMock(return_value=earth)

            mock_load.return_value = (ts_mock, eph_mock)

            result = service.compute_moon(12.97, 77.59, sample_dt, cloud_cover_pct=90.0)
            assert result.is_cloud_obscured is True

    def test_not_cloud_obscured_when_below_horizon(self, service, sample_dt):
        """Moon below horizon cannot be cloud-obscured."""
        with patch.object(AstronomyService, "_load_ephemeris") as mock_load:
            ts_mock = MagicMock()
            eph_mock = MagicMock()
            t_mock = MagicMock()
            ts_mock.from_datetime.return_value = t_mock

            alt_mock = MagicMock()
            alt_mock.degrees = -10.0
            az_mock = MagicMock()
            az_mock.degrees = 90.0
            dist_mock = MagicMock()
            sep_mock = MagicMock() 
            sep_mock.degrees = 90.0

            apparent = MagicMock()
            apparent.altaz.return_value = (alt_mock, az_mock, dist_mock)

            observe = MagicMock()
            observe.observe.return_value.apparent.return_value = apparent
            observe.observe.return_value.separation_from.return_value = sep_mock

            earth = MagicMock()
            earth.__add__ = MagicMock(return_value=earth)
            earth.at.return_value = observe
            eph_mock.__getitem__ = MagicMock(return_value=earth)

            mock_load.return_value = (ts_mock, eph_mock)

            result = service.compute_moon(12.97, 77.59, sample_dt, cloud_cover_pct=100.0)
            assert result.is_cloud_obscured is False


class TestComputePlanets:
    @patch.object(AstronomyService, "_load_ephemeris")
    def test_returns_list_of_planet_data(self, mock_load, service, sample_dt):
        ts_mock = MagicMock()
        eph_mock = MagicMock()
        ts_mock.from_datetime.return_value = MagicMock()

        alt_mock = MagicMock() 
        alt_mock.degrees = 20.0
        az_mock = MagicMock()
        az_mock.degrees = 90.0
        dist_mock = MagicMock()

        apparent = MagicMock()
        apparent.altaz.return_value = (alt_mock, az_mock, dist_mock)

        observe = MagicMock()
        observe.observe.return_value.apparent.return_value = apparent

        earth = MagicMock()
        earth.__add__ = MagicMock(return_value=earth)
        earth.at.return_value = observe
        eph_mock.__getitem__ = MagicMock(return_value=earth)

        mock_load.return_value = (ts_mock, eph_mock)

        planets = service.compute_planets(12.97, 77.59, sample_dt)

        assert len(planets) == 7  # all planets attempted
        for p in planets:
            assert p.name in {"Mercury", "Venus", "Mars", "Jupiter",
                              "Saturn", "Uranus", "Neptune"}
            assert isinstance(p.is_visible, bool)

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_planet_visible_above_threshold(self, mock_load, service, sample_dt):
        """Planet with altitude > 5° should be marked visible."""
        ts_mock = MagicMock()
        eph_mock = MagicMock()
        ts_mock.from_datetime.return_value = MagicMock()

        alt_mock = MagicMock()
        alt_mock.degrees = 30.0  # above 5° threshold
        az_mock = MagicMock()
        az_mock.degrees = 90.0
        dist_mock = MagicMock()

        apparent = MagicMock()
        apparent.altaz.return_value = (alt_mock, az_mock, dist_mock)

        observe = MagicMock()
        observe.observe.return_value.apparent.return_value = apparent

        earth = MagicMock()
        earth.__add__ = MagicMock(return_value=earth)
        earth.at.return_value = observe
        eph_mock.__getitem__ = MagicMock(return_value=earth)

        mock_load.return_value = (ts_mock, eph_mock)

        planets = service.compute_planets(12.97, 77.59, sample_dt)
        assert all(p.is_visible for p in planets)
