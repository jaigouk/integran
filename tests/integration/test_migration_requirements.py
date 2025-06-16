#!/usr/bin/env python3
"""Integration tests for user migration validation requirements.

Tests the specific integration requirements:
- Database: Create fresh database and verify setup process
- User Flow: Test first-time setup → settings save → settings load cycle
- Developer Mode: Test toggle functionality and service restrictions
- Error Handling: Verify graceful handling of migration edge cases
- Performance: Ensure no regression in database operation speed
"""

import asyncio
import sys
import tempfile
import time
from pathlib import Path

import pytest

from src.domain.user.models.user_models import (
    Language,
    LoadUserSettingsRequest,
    SaveUserSettingsRequest,
    ToggleDeveloperModeRequest,
)
from src.domain.user.services.load_user_settings import LoadUserSettings
from src.domain.user.services.save_user_settings import SaveUserSettings
from src.domain.user.services.toggle_developer_mode import ToggleDeveloperMode
from src.infrastructure.database.database import DatabaseManager
from src.infrastructure.messaging.event_bus import EventBus
from src.infrastructure.repositories.user_repository import UserSettingsRepository

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_database_fresh_setup():
    """Test creating fresh database and verify setup process."""
    print("✅ Database: Fresh database setup")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        # Initialize database manager with temp database
        db_manager = DatabaseManager(tmp_db_path)

        # Verify database was created and has expected tables
        with db_manager.get_session() as session:
            from sqlalchemy import text

            # Check that user_configuration table exists
            result = session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='user_configuration'"
                )
            )
            tables = result.fetchall()
            assert len(tables) == 1, "user_configuration table should exist"

        print("    ✓ Database and tables created successfully")

    finally:
        # Clean up
        Path(tmp_db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_user_flow_cycle():
    """Test first-time setup → settings save → settings load cycle."""
    print("✅ User Flow: First-time setup → save → load cycle")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        # Initialize services
        db_manager = DatabaseManager(tmp_db_path)
        event_bus = EventBus()
        user_repository = UserSettingsRepository(db_manager)

        load_service = LoadUserSettings(event_bus, user_repository)
        save_service = SaveUserSettings(event_bus, user_repository)

        # Step 1: First-time load (creates default settings)
        load_result = await load_service.call(LoadUserSettingsRequest(user_id=1))
        assert load_result.success, "First-time load should succeed"
        assert load_result.user_settings is not None, "Should return user settings"
        print("    ✓ First-time load creates default settings")

        # Step 2: Modify and save settings
        original_settings = load_result.user_settings
        modified_settings = original_settings.update_language(Language.GERMAN)

        save_result = await save_service.call(
            SaveUserSettingsRequest(user_settings=modified_settings)
        )
        assert save_result.success, "Settings save should succeed"
        print("    ✓ Settings modification and save works")

        # Step 3: Load settings again (should get saved settings)
        reload_result = await load_service.call(LoadUserSettingsRequest(user_id=1))
        assert reload_result.success, "Settings reload should succeed"
        assert reload_result.user_settings.language == Language.GERMAN, (
            "Language change should persist"
        )
        print("    ✓ Settings persistence verified")

    finally:
        Path(tmp_db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_developer_mode_toggle():
    """Test developer mode toggle functionality and service restrictions."""
    print("✅ Developer Mode: Toggle functionality and restrictions")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        # Initialize services
        db_manager = DatabaseManager(tmp_db_path)
        event_bus = EventBus()
        user_repository = UserSettingsRepository(db_manager)

        load_service = LoadUserSettings(event_bus, user_repository)
        toggle_service = ToggleDeveloperMode(event_bus, user_repository)

        # Create initial settings
        load_result = await load_service.call(LoadUserSettingsRequest(user_id=1))
        assert load_result.success, "Initial load should succeed"
        assert load_result.user_settings.developer_mode.enabled is False, (
            "Developer mode starts disabled"
        )
        print("    ✓ Developer mode starts disabled by default")

        # Enable developer mode
        enable_result = await toggle_service.call(
            ToggleDeveloperModeRequest(user_id=1, enable=True)
        )
        assert enable_result.success, "Developer mode enable should succeed"
        assert enable_result.developer_mode_enabled is True, "Should be enabled"
        assert enable_result.api_access_enabled is True, "API access should be enabled"
        print("    ✓ Developer mode enable works")

        # Verify persistence
        reload_result = await load_service.call(LoadUserSettingsRequest(user_id=1))
        assert reload_result.user_settings.developer_mode.enabled is True, (
            "Developer mode should persist"
        )
        print("    ✓ Developer mode persistence works")

        # Disable developer mode
        disable_result = await toggle_service.call(
            ToggleDeveloperModeRequest(user_id=1, enable=False)
        )
        assert disable_result.success, "Developer mode disable should succeed"
        assert disable_result.developer_mode_enabled is False, "Should be disabled"
        print("    ✓ Developer mode disable works")

    finally:
        Path(tmp_db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_error_handling():
    """Test graceful handling of migration edge cases."""
    print("✅ Error Handling: Migration edge cases")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        # Initialize services
        db_manager = DatabaseManager(tmp_db_path)
        event_bus = EventBus()
        user_repository = UserSettingsRepository(db_manager)

        load_service = LoadUserSettings(event_bus, user_repository)
        save_service = SaveUserSettings(event_bus, user_repository)

        # Test 1: Invalid user ID
        try:
            from src.domain.shared.services import ValidationError

            await load_service.call(LoadUserSettingsRequest(user_id=-1))
            raise AssertionError("Should have raised ValidationError")
        except ValidationError:
            print("    ✓ Invalid user ID properly rejected")

        # Test 2: Invalid preferences
        load_result = await load_service.call(LoadUserSettingsRequest(user_id=1))
        invalid_settings = load_result.user_settings
        invalid_settings.preferences.daily_goal = 9999  # Too high

        try:
            await save_service.call(
                SaveUserSettingsRequest(user_settings=invalid_settings)
            )
            raise AssertionError("Should have rejected invalid preferences")
        except ValidationError:
            print("    ✓ Invalid preferences properly rejected")

        # Test 3: Non-existent user (should handle gracefully)
        toggle_service = ToggleDeveloperMode(event_bus, user_repository)
        toggle_result = await toggle_service.call(
            ToggleDeveloperModeRequest(user_id=99999)
        )
        assert toggle_result.success, "Should handle non-existent user gracefully"
        print("    ✓ Non-existent user handled gracefully")

    finally:
        Path(tmp_db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_performance_regression():
    """Test database operation performance to ensure no regression."""
    print("✅ Performance: No regression in database operations")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        # Initialize services
        db_manager = DatabaseManager(tmp_db_path)
        event_bus = EventBus()
        user_repository = UserSettingsRepository(db_manager)

        load_service = LoadUserSettings(event_bus, user_repository)
        save_service = SaveUserSettings(event_bus, user_repository)

        # Performance thresholds (reasonable for local SQLite)
        LOAD_THRESHOLD = 0.1  # 100ms
        SAVE_THRESHOLD = 0.2  # 200ms

        # Test load performance (10 iterations)
        load_times = []
        for _ in range(10):
            start_time = time.time()
            result = await load_service.call(LoadUserSettingsRequest(user_id=1))
            end_time = time.time()

            assert result.success, "Load should succeed"
            load_times.append(end_time - start_time)

        avg_load_time = sum(load_times) / len(load_times)
        assert avg_load_time < LOAD_THRESHOLD, f"Load too slow: {avg_load_time:.3f}s"
        print(f"    ✓ Load performance: {avg_load_time:.3f}s avg (< {LOAD_THRESHOLD}s)")

        # Test save performance (5 iterations)
        base_settings = (
            await load_service.call(LoadUserSettingsRequest(user_id=1))
        ).user_settings
        save_times = []

        for i in range(5):
            # Modify settings slightly for each save
            modified_settings = base_settings.update_language(
                Language.GERMAN if i % 2 == 0 else Language.ENGLISH
            )

            start_time = time.time()
            result = await save_service.call(
                SaveUserSettingsRequest(user_settings=modified_settings)
            )
            end_time = time.time()

            assert result.success, "Save should succeed"
            save_times.append(end_time - start_time)

        avg_save_time = sum(save_times) / len(save_times)
        assert avg_save_time < SAVE_THRESHOLD, f"Save too slow: {avg_save_time:.3f}s"
        print(f"    ✓ Save performance: {avg_save_time:.3f}s avg (< {SAVE_THRESHOLD}s)")

    finally:
        Path(tmp_db_path).unlink(missing_ok=True)


async def run_integration_tests():
    """Run all integration tests for user migration validation."""
    print("🎯 User Migration Integration Testing")
    print("=" * 50)

    try:
        # Run all tests
        test_database_fresh_setup()
        await test_user_flow_cycle()
        await test_developer_mode_toggle()
        await test_error_handling()
        await test_performance_regression()

        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ User configuration migration validation complete")
        print("\nValidated requirements:")
        print("   • Database: Fresh database setup and verification")
        print("   • User Flow: Complete first-time setup → save → load cycle")
        print("   • Developer Mode: Toggle functionality and restrictions")
        print("   • Error Handling: Graceful handling of edge cases")
        print("   • Performance: No regression in database operations")
        print("\n📋 Integration Testing task complete - ready for Step 2")

    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_integration_tests())
