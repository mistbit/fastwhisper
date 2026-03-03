"""转录与说话人对齐服务"""
import logging
from typing import List

logger = logging.getLogger(__name__)


class TranscriptAligner:
    """将 Whisper 转录结果与说话人分离结果对齐"""

    def align(
        self,
        whisper_segments: List[dict],
        diarization_segments: List[dict],
    ) -> List[dict]:
        """
        对齐转录片段和说话人片段

        Args:
            whisper_segments: Whisper 输出 [{"start", "end", "text", "confidence"}]
            diarization_segments: pyannote 输出 [{"speaker", "start", "end"}]

        Returns:
            [{"speaker", "start", "end", "text", "confidence"}]
        """
        if not diarization_segments:
            # 没有说话人分离结果，使用默认说话人
            return [
                {
                    "speaker": "SPEAKER_01",
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                    "confidence": seg.get("confidence"),
                }
                for seg in whisper_segments
            ]

        aligned = []
        for ws in whisper_segments:
            # 找到与当前转录片段重叠最多的说话人片段
            best_speaker = None
            best_overlap = 0

            for ds in diarization_segments:
                overlap = self._calculate_overlap(
                    ws["start"],
                    ws["end"],
                    ds["start"],
                    ds["end"],
                )
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = ds["speaker"]

            aligned.append(
                {
                    "speaker": best_speaker or "UNKNOWN",
                    "start": ws["start"],
                    "end": ws["end"],
                    "text": ws["text"],
                    "confidence": ws.get("confidence"),
                }
            )

        # 合并相邻的同说话人片段
        aligned = self._merge_adjacent_segments(aligned)

        return aligned

    def _calculate_overlap(
        self,
        start1: float,
        end1: float,
        start2: float,
        end2: float,
    ) -> float:
        """计算两个时间区间的重叠比例"""
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)

        if overlap_start >= overlap_end:
            return 0

        overlap = overlap_end - overlap_start
        duration = end1 - start1

        return overlap / duration if duration > 0 else 0

    def _merge_adjacent_segments(self, segments: List[dict]) -> List[dict]:
        """合并相邻的同说话人片段"""
        if not segments:
            return segments

        merged = [segments[0]]

        for seg in segments[1:]:
            last = merged[-1]
            # 如果是同一个说话人且间隔小于1秒，合并
            if seg["speaker"] == last["speaker"] and seg["start"] - last["end"] < 1.0:
                last["end"] = seg["end"]
                last["text"] += " " + seg["text"]
            else:
                merged.append(seg)

        return merged


# 单例实例
transcript_aligner = TranscriptAligner()