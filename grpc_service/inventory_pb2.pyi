from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class CheckStockRequest(_message.Message):
    __slots__ = ("item_id", "quantity", "delay_seconds")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    DELAY_SECONDS_FIELD_NUMBER: _ClassVar[int]
    item_id: str
    quantity: int
    delay_seconds: float
    def __init__(self, item_id: _Optional[str] = ..., quantity: _Optional[int] = ..., delay_seconds: _Optional[float] = ...) -> None: ...

class CheckStockResponse(_message.Message):
    __slots__ = ("item_id", "name", "available", "current_stock", "price", "message")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    CURRENT_STOCK_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    item_id: str
    name: str
    available: bool
    current_stock: int
    price: float
    message: str
    def __init__(self, item_id: _Optional[str] = ..., name: _Optional[str] = ..., available: _Optional[bool] = ..., current_stock: _Optional[int] = ..., price: _Optional[float] = ..., message: _Optional[str] = ...) -> None: ...

class CreateOrderRequest(_message.Message):
    __slots__ = ("item_id", "quantity", "delay_seconds")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    DELAY_SECONDS_FIELD_NUMBER: _ClassVar[int]
    item_id: str
    quantity: int
    delay_seconds: float
    def __init__(self, item_id: _Optional[str] = ..., quantity: _Optional[int] = ..., delay_seconds: _Optional[float] = ...) -> None: ...

class CreateOrderResponse(_message.Message):
    __slots__ = ("order_id", "item_id", "quantity", "status", "total_price", "message")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_PRICE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    item_id: str
    quantity: int
    status: str
    total_price: float
    message: str
    def __init__(self, order_id: _Optional[str] = ..., item_id: _Optional[str] = ..., quantity: _Optional[int] = ..., status: _Optional[str] = ..., total_price: _Optional[float] = ..., message: _Optional[str] = ...) -> None: ...
