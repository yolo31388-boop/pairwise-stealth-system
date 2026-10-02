import pytest
from stealth.system import StealthSystem


class TestStealthSystem:

    def test_calculate_detection(self):
        """侦测计算不做视线遮挡，墙后面也能被看到"""
        obj = StealthSystem()
        result = obj.calculate_detection()
        self.assertIsNotNone(result)

    def test_calculate_noise(self):
        """噪音计算不做材质区分，地毯和地板脚步声一样"""
        obj = StealthSystem()
        result = obj.calculate_noise()
        self.assertIsNotNone(result)

    def test_check_hiding_spot(self):
        """隐藏点不做有效性检查，暴露的位置也能藏"""
        obj = StealthSystem()
        result = obj.check_hiding_spot()
        self.assertIsNotNone(result)

    def test_update_alertness(self):
        """警觉度不做衰减，被看到一次永远警戒"""
        obj = StealthSystem()
        result = obj.update_alertness()
        self.assertIsNotNone(result)

    def test_calculate_stealth_score(self):
        """潜行得分不做时间奖励，慢通关和快通关分数一样"""
        obj = StealthSystem()
        result = obj.calculate_stealth_score()
        self.assertIsNotNone(result)

