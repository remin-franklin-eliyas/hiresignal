from pydantic import BaseModel, ConfigDict, Field


class ResourceData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    odata_type: str | None = Field(default=None, alias="@odata.type")
    odata_id: str | None = Field(default=None, alias="@odata.id")
    odata_etag: str | None = Field(default=None, alias="@odata.etag")
    id: str


class ChangeNotification(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    subscription_id: str = Field(alias="subscriptionId")
    subscription_expiration_date_time: str | None = Field(
        default=None,
        alias="subscriptionExpirationDateTime",
    )
    client_state: str | None = Field(default=None, alias="clientState")
    change_type: str = Field(alias="changeType")
    resource: str
    tenant_id: str | None = Field(default=None, alias="tenantId")
    resource_data: ResourceData | None = Field(default=None, alias="resourceData")

    @property
    def message_id(self) -> str | None:
        if self.resource_data is not None:
            return self.resource_data.id
        parts = [part for part in self.resource.split("/") if part]
        return parts[-1] if parts else None


class ChangeNotificationCollection(BaseModel):
    value: list[ChangeNotification]


class ManualReviewItem(BaseModel):
    reason: str
    message_id: str | None = None
    attachment_name: str | None = None
    subscription_id: str | None = None

