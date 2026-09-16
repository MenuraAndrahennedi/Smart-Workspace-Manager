import json

import pandas as pd


def dataframe_to_records(dataframe: pd.DataFrame) -> list[dict]:
    return json.loads(
        dataframe.to_json(
            orient="records",
            date_format="iso",
        )
    )
