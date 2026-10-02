"""
pairwise-stealth-system - StealthSystem

This module contains a deliberately broken implementation.
Fix all bugs so that tests pass.
"""


class StealthSystem:
    def __init__(self):
        self.state = {}

    def calculate_detection(self, *args, **kwargs):
        """BUG: 侦测计算不做视线遮挡，墙后面也能被看到"""
        return None

    def calculate_noise(self, *args, **kwargs):
        """BUG: 噪音计算不做材质区分，地毯和地板脚步声一样"""
        return None

    def check_hiding_spot(self, *args, **kwargs):
        """BUG: 隐藏点不做有效性检查，暴露的位置也能藏"""
        return None

    def update_alertness(self, *args, **kwargs):
        """BUG: 警觉度不做衰减，被看到一次永远警戒"""
        return None

    def calculate_stealth_score(self, *args, **kwargs):
        """BUG: 潜行得分不做时间奖励，慢通关和快通关分数一样"""
        return None

