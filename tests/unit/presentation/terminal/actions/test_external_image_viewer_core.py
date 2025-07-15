"""Core tests for ExternalImageViewer dynamic layout functionality."""

from PIL import Image as PILImage

from src.presentation.terminal.actions.external_image_viewer import ExternalImageViewer


class TestCreateComposite:
    """Test the _create_composite method with different image counts - core functionality."""

    def test_single_image_layout(self):
        """Test composite creation with 1 image - should be centered and full size."""
        # Create single test image
        img = PILImage.new("RGB", (200, 150), "red")
        images = [img]

        composite = ExternalImageViewer._create_composite(
            images, question_id=123, question_text="Test question"
        )

        # Check composite dimensions for single image layout
        expected_width = 200 + 30 * 2  # image_width + padding * 2
        expected_height = 150 + 30 * 2 + 80  # image_height + padding * 2 + title_height

        assert composite.width == expected_width
        assert composite.height == expected_height

    def test_two_images_layout(self):
        """Test composite creation with 2 images - should be horizontal layout."""
        # Create two test images
        img1 = PILImage.new("RGB", (100, 80), "red")
        img2 = PILImage.new("RGB", (100, 80), "blue")
        images = [img1, img2]

        composite = ExternalImageViewer._create_composite(
            images, question_id=456, question_text="Two image test"
        )

        # Check composite dimensions for two image layout
        expected_width = 100 * 2 + 30 * 3  # max_width * 2 + padding * 3
        expected_height = 80 + 30 * 2 + 80  # max_height + padding * 2 + title_height

        assert composite.width == expected_width
        assert composite.height == expected_height

    def test_three_images_layout(self):
        """Test composite creation with 3 images - should use 2x2 grid."""
        # Create three test images
        images = [
            PILImage.new("RGB", (120, 100), "red"),
            PILImage.new("RGB", (120, 100), "blue"),
            PILImage.new("RGB", (120, 100), "green"),
        ]

        composite = ExternalImageViewer._create_composite(
            images, question_id=789, question_text="Three image test"
        )

        # Check composite dimensions for 2x2 grid layout
        expected_width = 120 * 2 + 30 * 3  # max_width * 2 + padding * 3
        expected_height = (
            100 * 2 + 30 * 3 + 80
        )  # max_height * 2 + padding * 3 + title_height

        assert composite.width == expected_width
        assert composite.height == expected_height

    def test_four_images_layout(self):
        """Test composite creation with 4 images - should use 2x2 grid."""
        # Create four test images
        images = [
            PILImage.new("RGB", (150, 120), "red"),
            PILImage.new("RGB", (150, 120), "blue"),
            PILImage.new("RGB", (150, 120), "green"),
            PILImage.new("RGB", (150, 120), "yellow"),
        ]

        composite = ExternalImageViewer._create_composite(
            images, question_id=999, question_text="Four image test"
        )

        # Check composite dimensions for 2x2 grid layout
        expected_width = 150 * 2 + 30 * 3  # max_width * 2 + padding * 3
        expected_height = (
            120 * 2 + 30 * 3 + 80
        )  # max_height * 2 + padding * 3 + title_height

        assert composite.width == expected_width
        assert composite.height == expected_height

    def test_mismatched_image_dimensions(self):
        """Test composite with images of different sizes."""
        # Create images with very different dimensions
        images = [
            PILImage.new("RGB", (50, 200), "red"),  # tall and narrow
            PILImage.new("RGB", (300, 100), "blue"),  # wide and short
            PILImage.new("RGB", (150, 150), "green"),  # square
        ]

        composite = ExternalImageViewer._create_composite(
            images, question_id=111, question_text="Mismatched sizes"
        )

        # Should use the maximum dimensions
        max_width = 300
        max_height = 200
        expected_width = max_width * 2 + 30 * 3
        expected_height = max_height * 2 + 30 * 3 + 80

        assert composite.width == expected_width
        assert composite.height == expected_height

    def test_layout_differences_validate_fix(self):
        """Validate that single image layout differs from multi-image layout (the fix)."""
        # Single image
        single_img = [PILImage.new("RGB", (200, 150), "red")]
        single_composite = ExternalImageViewer._create_composite(
            single_img, question_id=1, question_text="Single"
        )

        # Four images (old behavior would force this layout for single images too)
        four_imgs = [PILImage.new("RGB", (200, 150), "red") for _ in range(4)]
        four_composite = ExternalImageViewer._create_composite(
            four_imgs, question_id=2, question_text="Four"
        )

        # Single image should be smaller (not 2x2 grid)
        assert single_composite.width < four_composite.width
        assert single_composite.height < four_composite.height

        # Single image dimensions should be: image + padding (not 2x image + padding)
        expected_single_width = 200 + 60  # image_width + 2*padding
        expected_single_height = (
            150 + 140
        )  # image_height + 2*padding + title_height (80)

        assert single_composite.width == expected_single_width
        assert single_composite.height == expected_single_height


class TestCreatePlaceholder:
    """Test placeholder creation functionality."""

    def test_create_placeholder_basic(self):
        """Test creating a placeholder image."""
        placeholder = ExternalImageViewer._create_placeholder("A", "/test/image.png")

        assert placeholder is not None
        assert isinstance(placeholder, PILImage.Image)
        assert placeholder.size == (400, 400)

    def test_create_placeholder_different_letters(self):
        """Test creating placeholders with different option letters."""
        letters = ["A", "B", "C", "D"]

        for letter in letters:
            placeholder = ExternalImageViewer._create_placeholder(
                letter, f"/test/image_{letter}.png"
            )
            assert placeholder is not None
            assert isinstance(placeholder, PILImage.Image)


class TestGetFont:
    """Test font loading functionality."""

    def test_get_font_returns_object(self):
        """Test that _get_font returns a font object."""
        font = ExternalImageViewer._get_font(20)
        assert font is not None

    def test_get_font_different_sizes(self):
        """Test getting fonts with different sizes."""
        sizes = [8, 16, 24, 48]
        for size in sizes:
            font = ExternalImageViewer._get_font(size)
            assert font is not None
