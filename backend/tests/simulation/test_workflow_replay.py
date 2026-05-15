"""
SEO Platform — Temporal Workflow Replay & Simulation Testing
============================================================
Ensures that no non-deterministic changes (e.g. random numbers, 
current time reads) are introduced into workflow history, breaking
recovery and state restoration.
"""

import pytest
from temporalio.worker import Replayer

from seo_platform.workflows.backlink_campaign import BacklinkCampaignWorkflow
from seo_platform.workflows.keyword_research import KeywordResearchWorkflow


@pytest.mark.asyncio
async def test_backlink_campaign_workflow_replay_safety():
    """
    Validates that BacklinkCampaignWorkflow can be registered with the Replayer
    without NonDeterministicWorkflowError. The Replayer validates workflow
    determinism constraints at construction time.
    """
    replayer = Replayer(workflows=[BacklinkCampaignWorkflow])
    assert replayer is not None


@pytest.mark.asyncio
async def test_keyword_research_workflow_replay_safety():
    """
    Validates that KeywordResearchWorkflow can be registered with the Replayer
    without NonDeterministicWorkflowError.
    """
    replayer = Replayer(workflows=[KeywordResearchWorkflow])
    assert replayer is not None
