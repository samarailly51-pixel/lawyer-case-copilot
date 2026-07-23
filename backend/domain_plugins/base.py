from __future__ import annotations

from abc import ABC, abstractmethod


class DomainPlugin(ABC):
    case_types: tuple[str, ...]

    @abstractmethod
    def document_categories(self) -> tuple[str, ...]: ...

    @abstractmethod
    def workflow_nodes(self) -> tuple[str, ...]: ...

    @abstractmethod
    def rule_files(self) -> tuple[str, ...]: ...


class GeneralPlugin(DomainPlugin):
    case_types = ("contract", "labor", "general_civil", "other")

    def document_categories(self):
        return ("身份主体材料", "合同及协议", "沟通记录", "付款凭证", "行政或司法文书", "其他证据")

    def workflow_nodes(self):
        return ("fact_extraction", "timeline_builder", "evidence_matrix", "risk_issue")

    def rule_files(self):
        return ("rules/general/missing_materials.yaml",)

