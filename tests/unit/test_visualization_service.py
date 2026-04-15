from app.services.visualization_service import VisualizationService
from app.services.narration_service import NarrationService

from unittest.mock import patch
from app.services.geocoding_service import GeocodingService

@patch("app.services.geocoding_service.requests.get")
def test_geocoding(mock_get):
    mock_get.return_value.json.return_value = [{"lat": "12.97", "lon": "77.59"}]

    service = GeocodingService()
    result = service.geocode("Bangalore")

    assert result is not None

def test_visualization_basic():
    service = VisualizationService()
    result = service.generate_chart(data={})
    assert result is not None


def test_visualization_empty_input():
    service = VisualizationService()
    result = service.generate_chart(data=None)
    assert result is not None


def test_narration_basic():
    service = NarrationService()
    result = service.generate("Clear sky tonight")
    assert isinstance(result, str)


def test_narration_empty():
    service = NarrationService()
    result = service.generate("")
    assert result is not None