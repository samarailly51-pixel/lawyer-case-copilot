from domain_plugins.base import DomainPlugin


class TrafficInjuryPlugin(DomainPlugin):
    case_types = ("traffic_injury",)

    def document_categories(self):
        return (
            "道路交通事故认定书", "车辆及保险材料", "门诊病历", "住院病历", "出院记录",
            "医疗费用票据", "医疗费用清单", "伤残鉴定材料", "收入及误工证明", "护理证明",
            "户籍及居住证明", "被扶养人材料", "交通费和辅助器具材料", "调解、协商及诉讼材料",
        )

    def workflow_nodes(self):
        return ("traffic_injury_module", "evidence_matrix", "risk_issue")

    def rule_files(self):
        return (
            "rules/traffic_injury/evidence_completeness.yaml",
            "rules/traffic_injury/personal_experience_rules.yaml",
        )

