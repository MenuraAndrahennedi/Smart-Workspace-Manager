from pydantic import BaseModel


class XLSXConvertRequest(BaseModel):
    sheet_name: str