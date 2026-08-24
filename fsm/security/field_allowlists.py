CUSTOMER_REGISTRATION_FIELDS = {"full_name", "email", "password", "phone"}
GUEST_BOOKING_FIELDS = {
	"customer_name",
	"contact_phone",
	"service_address",
	"service_type",
	"preferred_date",
	"notes",
}
INTEGRATION_JOB_FIELDS = {
	"company",
	"customer",
	"service_type",
	"scheduled_date",
	"priority",
	"service_address",
	"items",
}
INTEGRATION_JOB_ITEM_FIELDS = {"item_code", "qty", "rate"}
MESSAGE_FIELDS = {"job", "message"}
FEEDBACK_FIELDS = {"job", "rating", "comments", "nps_score"}
