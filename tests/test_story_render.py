"""Targeted checks for Story exporter frame equivalence."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'engine/.packages'),str(ROOT/'engine')]
from story_render import pixel_buffers_equivalent


class StoryRenderTests(unittest.TestCase):
    def test_exact_pixels_match(self):
        frame=bytes([10,20,30])*1001
        self.assertTrue(pixel_buffers_equivalent(frame,frame,1001))

    def test_one_level_compositor_rounding_is_accepted(self):
        first=bytearray(bytes([10,20,30])*1001);second=bytearray(first)
        second[2]+=1
        self.assertTrue(pixel_buffers_equivalent(first,second,1001))

    def test_larger_color_delta_is_rejected(self):
        first=bytearray(bytes([10,20,30])*1001);second=bytearray(first)
        second[2]+=2
        self.assertFalse(pixel_buffers_equivalent(first,second,1001))

    def test_point_one_percent_changed_pixels_is_rejected(self):
        first=bytearray(bytes([10,20,30])*1000);second=bytearray(first)
        second[2]+=1
        self.assertFalse(pixel_buffers_equivalent(first,second,1000))


if __name__=='__main__':unittest.main()
