from dataclasses import dataclass


@dataclass
class SourceProfile:
    name: str
    source_type: str
    reliability: float
    official: bool


class SourceReliability:

    def __init__(self):

        self.sources = {
            "federal_reserve": SourceProfile(
                name="Federal Reserve",
                source_type="CENTRAL_BANK",
                reliability=1.00,
                official=True,
            ),

            "bls": SourceProfile(
                name="U.S. Bureau of Labor Statistics",
                source_type="GOVERNMENT",
                reliability=1.00,
                official=True,
            ),

            "white_house": SourceProfile(
                name="White House",
                source_type="GOVERNMENT",
                reliability=1.00,
                official=True,
            ),

            "reuters": SourceProfile(
                name="Reuters",
                source_type="NEWS",
                reliability=0.90,
                official=False,
            ),

            "ap": SourceProfile(
                name="Associated Press",
                source_type="NEWS",
                reliability=0.90,
                official=False,
            ),

            "unknown": SourceProfile(
                name="Unknown Source",
                source_type="UNKNOWN",
                reliability=0.20,
                official=False,
            ),
        }

    def get(self, source_id):

        return self.sources.get(
            source_id,
            self.sources["unknown"],
        )

    def score(self, source_id):

        source = self.get(source_id)

        return {
            "source": source.name,
            "source_type": source.source_type,
            "reliability": source.reliability,
            "official": source.official,
        }


if __name__ == "__main__":

    engine = SourceReliability()

    for source in [
        "federal_reserve",
        "bls",
        "white_house",
        "reuters",
        "unknown",
    ]:
        print(
            engine.score(source)
        )
