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
    def _create_altitude_mock(self, degrees):
        """Create a mock for altitude that has a .degrees attribute."""
        alt_mock = MagicMock()
        alt_mock.degrees = degrees
        return alt_mock

    def _create_azimuth_mock(self, degrees):
        """Create a mock for azimuth that has a .degrees attribute."""
        az_mock = MagicMock()
        az_mock.degrees = degrees
        return az_mock

    def _create_moon_mocks(self, alt_deg=30.0, az_deg=90.0, elongation_deg=180.0):
        """Helper to create reusable moon test mocks."""
        ts_mock = MagicMock()
        eph_mock = MagicMock()
        t_mock = MagicMock()
        ts_mock.from_datetime.return_value = t_mock

        # Create altitude and azimuth mocks with .degrees attributes
        alt_mock = self._create_altitude_mock(alt_deg)
        az_mock = self._create_azimuth_mock(az_deg)
        dist_mock = MagicMock()

        # Create a tuple that can be unpacked: (alt, az, dist)
        altaz_tuple = (alt_mock, az_mock, dist_mock)

        # Elongation for phase calculation
        sep_mock = MagicMock()
        sep_mock.degrees = elongation_deg

        # The apparent object has altaz() method that returns the unpacked tuple
        apparent = MagicMock()
        # Make altaz() return the actual tuple (not a mock) so unpacking works
        apparent.altaz.return_value = altaz_tuple

        # observation.observe() must handle both moon and sun calls
        def observe_factory(body):
            """Returns appropriate mock for moon or sun."""
            observe_mock = MagicMock()
            # For moon: observe(moon).apparent() returns altitude/azimuth
            observe_mock.apparent.return_value = apparent
            # For moon: observe(moon).separation_from(sun) returns elongation
            observe_mock.separation_from.return_value = sep_mock
            return observe_mock

        observation = MagicMock()
        observation.observe.side_effect = observe_factory

        # location = earth + wgs84.latlon(lat, lon)
        location = MagicMock()
        location.at.return_value = observation

        # earth.__add__ returns location
        earth = MagicMock()
        earth.__add__.return_value = location

        def eph_getitem(key):
            if key == "earth":
                return earth
            # Return a mock for moon/sun that can be compared
            return MagicMock(name=key)

        eph_mock.__getitem__.side_effect = eph_getitem
        
        return (ts_mock, eph_mock)

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_returns_moon_data(self, mock_load, service, sample_dt):
        """compute_moon should return a MoonData object with correct types."""
        ts_mock, eph_mock = self._create_moon_mocks()
        mock_load.return_value = (ts_mock, eph_mock)

        moon_data = service.compute_moon(12.97, 77.59, sample_dt, cloud_cover_pct=0.0)

        assert moon_data.phase_name in {
            "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
            "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent",
        }
        assert 0 <= moon_data.illumination_pct <= 100
        assert isinstance(moon_data.is_above_horizon, bool)
        assert isinstance(moon_data.is_cloud_obscured, bool)

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_cloud_obscured_when_above_horizon_and_high_clouds(self, mock_load, service, sample_dt):
        """Moon above horizon + >70% cloud cover => is_cloud_obscured = True."""
        ts_mock, eph_mock = self._create_moon_mocks(alt_deg=30.0, elongation_deg=180.0)
        mock_load.return_value = (ts_mock, eph_mock)

        result = service.compute_moon(12.97, 77.59, sample_dt, cloud_cover_pct=90.0)
        
        assert result.is_above_horizon is True, f"Moon should be above horizon (alt=30°), got alt={result.altitude_deg}"
        assert result.is_cloud_obscured is True, "Moon should be cloud obscured (90% clouds > 70% threshold)"

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_not_cloud_obscured_when_below_horizon(self, mock_load, service, sample_dt):
        """Moon below horizon cannot be cloud-obscured."""
        ts_mock, eph_mock = self._create_moon_mocks(alt_deg=-10.0, elongation_deg=90.0)
        mock_load.return_value = (ts_mock, eph_mock)

        result = service.compute_moon(12.97, 77.59, sample_dt, cloud_cover_pct=100.0)
        
        assert result.is_above_horizon is False, f"Moon should be below horizon (alt=-10°), got alt={result.altitude_deg}"
        assert result.is_cloud_obscured is False, "Moon below horizon cannot be obscured"

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_not_cloud_obscured_when_low_cloud_cover(self, mock_load, service, sample_dt):
        """Moon above horizon but low clouds (<70%) => not obscured."""
        ts_mock, eph_mock = self._create_moon_mocks(alt_deg=45.0, elongation_deg=180.0)
        mock_load.return_value = (ts_mock, eph_mock)

        result = service.compute_moon(12.97, 77.59, sample_dt, cloud_cover_pct=50.0)
        
        assert result.is_above_horizon is True, f"Moon should be above horizon (alt=45°), got alt={result.altitude_deg}"
        assert result.is_cloud_obscured is False, "Cloud cover 50% < 70% threshold"

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_moon_illumination_ranges(self, mock_load, service, sample_dt):
        """Test moon illumination at different elongation angles."""
        # New Moon: elongation ~ 0°
        ts_mock, eph_mock = self._create_moon_mocks(elongation_deg=10.0)
        mock_load.return_value = (ts_mock, eph_mock)
        result = service.compute_moon(12.97, 77.59, sample_dt)
        assert result.illumination_pct < 10, "Near new moon should have low illumination"

        # Full Moon: elongation ~ 180°
        ts_mock, eph_mock = self._create_moon_mocks(elongation_deg=180.0)
        mock_load.return_value = (ts_mock, eph_mock)
        result = service.compute_moon(12.97, 77.59, sample_dt)
        assert result.illumination_pct > 95, "Full moon should have high illumination"

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_moon_phase_name_matches_elongation(self, mock_load, service, sample_dt):
        """Test that moon phase name matches the elongation angle."""
        ts_mock, eph_mock = self._create_moon_mocks(elongation_deg=90.0)
        mock_load.return_value = (ts_mock, eph_mock)
        result = service.compute_moon(12.97, 77.59, sample_dt)
        assert result.phase_name == "First Quarter"


class TestComputePlanets:
    def _create_altitude_mock(self, degrees):
        """Create a mock for altitude that has a .degrees attribute."""
        alt_mock = MagicMock()
        alt_mock.degrees = degrees
        return alt_mock

    def _create_azimuth_mock(self, degrees):
        """Create a mock for azimuth that has a .degrees attribute."""
        az_mock = MagicMock()
        az_mock.degrees = degrees
        return az_mock

    def _create_planet_mocks(self, alt_deg=20.0, az_deg=90.0):
        """Helper to create reusable planet test mocks."""
        ts_mock = MagicMock()
        eph_mock = MagicMock()
        ts_mock.from_datetime.return_value = MagicMock()

        # Create altitude and azimuth mocks
        alt_mock = self._create_altitude_mock(alt_deg)
        az_mock = self._create_azimuth_mock(az_deg)
        dist_mock = MagicMock()

        # Create a tuple that can be unpacked
        altaz_tuple = (alt_mock, az_mock, dist_mock)

        # apparent object with altaz() method
        apparent = MagicMock()
        apparent.altaz.return_value = altaz_tuple

        # observer.observe(planet).apparent() returns apparent
        planet_observe = MagicMock()
        planet_observe.apparent.return_value = apparent

        observer = MagicMock()
        observer.observe.return_value = planet_observe

        # location = earth + wgs84.latlon(lat, lon)
        location = MagicMock()
        location.at.return_value = observer

        # earth.__add__ returns location
        earth = MagicMock()
        earth.__add__.return_value = location

        def eph_getitem(key):
            if key == "earth":
                return earth
            return MagicMock(name=key)

        eph_mock.__getitem__.side_effect = eph_getitem
        
        return (ts_mock, eph_mock)

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_returns_list_of_planet_data(self, mock_load, service, sample_dt):
        """compute_planets should return a list of PlanetData for all planets."""
        ts_mock, eph_mock = self._create_planet_mocks()
        mock_load.return_value = (ts_mock, eph_mock)

        planets = service.compute_planets(12.97, 77.59, sample_dt)

        assert len(planets) == 7  # all planets attempted
        for p in planets:
            assert p.name in {"Mercury", "Venus", "Mars", "Jupiter",
                              "Saturn", "Uranus", "Neptune"}
            assert isinstance(p.is_visible, bool)
            assert isinstance(p.altitude_deg, float)
            assert isinstance(p.azimuth_deg, float)

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_planet_visible_above_threshold(self, mock_load, service, sample_dt):
        """Planet with altitude > 5° should be marked visible."""
        ts_mock, eph_mock = self._create_planet_mocks(alt_deg=30.0)
        mock_load.return_value = (ts_mock, eph_mock)

        planets = service.compute_planets(12.97, 77.59, sample_dt)
        
        # All planets should have altitude > 5° and thus be visible
        assert all(p.is_visible for p in planets), \
            f"Expected all planets visible with altitude=30°, but got: {[(p.name, p.is_visible, p.altitude_deg) for p in planets]}"

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_planet_not_visible_below_threshold(self, mock_load, service, sample_dt):
        """Planet with altitude <= 5° should NOT be marked visible."""
        ts_mock, eph_mock = self._create_planet_mocks(alt_deg=2.0)
        mock_load.return_value = (ts_mock, eph_mock)

        planets = service.compute_planets(12.97, 77.59, sample_dt)
        
        # No planets should be visible with altitude=2°
        assert not any(p.is_visible for p in planets), \
            f"Expected no planets visible with altitude=2°, but got: {[(p.name, p.is_visible, p.altitude_deg) for p in planets]}"

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_planet_visibility_at_boundary(self, mock_load, service, sample_dt):
        """Planet with altitude = 5° should NOT be visible (must be > 5°)."""
        ts_mock, eph_mock = self._create_planet_mocks(alt_deg=5.0)
        mock_load.return_value = (ts_mock, eph_mock)

        planets = service.compute_planets(12.97, 77.59, sample_dt)
        
        # At exactly 5°, none should be visible (must be strictly > 5°)
        assert not any(p.is_visible for p in planets), \
            "Expected no planets visible at exactly 5° altitude (threshold is >5°)"

    @patch.object(AstronomyService, "_load_ephemeris")
    def test_all_planets_are_computed(self, mock_load, service, sample_dt):
        """Test that all 7 planets are computed and named correctly."""
        ts_mock, eph_mock = self._create_planet_mocks(alt_deg=20.0)
        mock_load.return_value = (ts_mock, eph_mock)

        planets = service.compute_planets(12.97, 77.59, sample_dt)
        
        planet_names = {p.name for p in planets}
        expected_names = {"Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"}
        assert planet_names == expected_names, f"Expected {expected_names}, got {planet_names}"


class TestLocalSiderealTime:
    @patch.object(AstronomyService, "_load_ephemeris")
    def test_local_sidereal_time(self, mock_load, service, sample_dt):
        """Test local sidereal time calculation."""
        ts_mock = MagicMock()
        eph_mock = MagicMock()
        
        t_mock = MagicMock()
        t_mock.gmst = 12.5  # Greenwich Mean Sidereal Time
        ts_mock.from_datetime.return_value = t_mock
        
        mock_load.return_value = (ts_mock, eph_mock)
        
        # longitude = 77.59° (roughly 5.17 hours in sidereal time)
        lst = service.local_sidereal_time(77.59, sample_dt)
        
        # LST = GMST + longitude/15
        # LST = 12.5 + 77.59/15 = 12.5 + 5.1727 = 17.6727
        expected_lst = (12.5 + 77.59 / 15.0) % 24
        assert lst == pytest.approx(expected_lst, abs=0.01)