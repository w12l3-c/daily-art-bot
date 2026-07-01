import logging

import artbot.shared as shared
from artbot.BotConfig import BotConfig
from artbot.DiscordMessageSender import DiscordMessageSender
from artbot.core.chain.ChainService import ChainService, default_chain_service
from artbot.core.challenge.ChallengeService import (
    ChallengeService,
    default_challenge_service,
)
from artbot.core.daily.DailyService import DailyService, default_daily_service
from artbot.core.duel.DuelService import DuelService, default_duel_service
from artbot.core.wcw.WcwService import WcwService, default_wcw_service
from artbot.persistence.DailyStateRepository import DailyStateRepository
from artbot.persistence.WcwStateRepository import WcwStateRepository


class AppContext:
    def __init__(
        self,
        config: BotConfig,
        logger: logging.Logger,
        message_sender: DiscordMessageSender,
        daily_state_repository: DailyStateRepository,
        wcw_state_repository: WcwStateRepository,
        daily_service: DailyService,
        wcw_service: WcwService,
        challenge_service: ChallengeService,
        duel_service: DuelService,
        chain_service: ChainService,
    ) -> None:
        self.config = config
        self.bot = shared.bot
        self.logger = logger
        self.message_sender = message_sender
        self.daily_state_repository = daily_state_repository
        self.wcw_state_repository = wcw_state_repository
        self.daily_service = daily_service
        self.wcw_service = wcw_service
        self.challenge_service = challenge_service
        self.duel_service = duel_service
        self.chain_service = chain_service

    @classmethod
    def from_shared(cls) -> "AppContext":
        config = BotConfig.from_shared(shared)
        return cls(
            config=config,
            logger=shared.logger,
            message_sender=DiscordMessageSender(),
            daily_state_repository=DailyStateRepository(config.daily_state_path),
            wcw_state_repository=WcwStateRepository(config.wcw_state_path),
            daily_service=default_daily_service,
            wcw_service=default_wcw_service,
            challenge_service=default_challenge_service,
            duel_service=default_duel_service,
            chain_service=default_chain_service,
        )
