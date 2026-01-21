"""
Base scenario components and utilities for composable scenario generation.

This module provides reusable building blocks for constructing complex scenarios
from simple, composable components.

REFACTORED: Components have been moved to scenarios/components/ and scenarios/common/.
This file now re-exports them for backward compatibility.
"""

# Re-export Resource Managers
from scenarios.common.resource_managers import StationManager, TimeManager, TrainManager

# Re-export Builders
from scenarios.common.builders import MessageBuilder, ContextBuilder, ToolCallBuilder

# Re-export Components
from scenarios.components.search_component import SearchComponent
from scenarios.components.purchase_component import PurchaseComponent
from scenarios.components.qa_component import QAComponent
from scenarios.components.refusal_component import RefusalComponent
from scenarios.components.greeting_component import GreetingComponent
from scenarios.components.confirmation_component import ConfirmationComponent
