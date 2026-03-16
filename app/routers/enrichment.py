import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.core import findymail_client
from app.models.enrichment import (
    EnrichCompanyRequest,
    FindEmailRequest,
    FindPhoneRequest,
    GenerateLeadListRequest,
    GetLeadListResultsRequest,
    ReverseEmailLookupRequest,
    VerifyEmailRequest,
)

logger = logging.getLogger("clay-webhook-os")

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


def _check_key() -> JSONResponse | None:
    if not settings.findymail_api_key:
        return JSONResponse(
            status_code=503,
            content={"error": True, "error_message": "Findymail API key not configured"},
        )
    return None


@router.post("/find-email")
async def find_email(body: FindEmailRequest, request: Request):
    err = _check_key()
    if err:
        return err
    result = await findymail_client.find_email(
        name=body.name,
        domain=body.domain,
        linkedin_url=body.linkedin_url,
        api_key=settings.findymail_api_key,
        base_url=settings.findymail_base_url,
        timeout=settings.findymail_timeout,
    )
    return result


@router.post("/find-phone")
async def find_phone(body: FindPhoneRequest, request: Request):
    err = _check_key()
    if err:
        return err
    result = await findymail_client.find_phone(
        linkedin_url=body.linkedin_url,
        api_key=settings.findymail_api_key,
        base_url=settings.findymail_base_url,
        timeout=settings.findymail_timeout,
    )
    return result


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, request: Request):
    err = _check_key()
    if err:
        return err
    result = await findymail_client.verify_email(
        email=body.email,
        api_key=settings.findymail_api_key,
        base_url=settings.findymail_base_url,
        timeout=settings.findymail_timeout,
    )
    return result


@router.post("/reverse-lookup")
async def reverse_lookup(body: ReverseEmailLookupRequest, request: Request):
    err = _check_key()
    if err:
        return err
    result = await findymail_client.reverse_email_lookup(
        email=body.email,
        with_profile=body.with_profile,
        api_key=settings.findymail_api_key,
        base_url=settings.findymail_base_url,
        timeout=settings.findymail_timeout,
    )
    return result


@router.post("/enrich-company")
async def enrich_company(body: EnrichCompanyRequest, request: Request):
    err = _check_key()
    if err:
        return err
    result = await findymail_client.enrich_company(
        domain=body.domain,
        linkedin_url=body.linkedin_url,
        name=body.name,
        api_key=settings.findymail_api_key,
        base_url=settings.findymail_base_url,
        timeout=settings.findymail_timeout,
    )
    return result


@router.post("/generate-leads")
async def generate_leads(body: GenerateLeadListRequest, request: Request):
    err = _check_key()
    if err:
        return err
    result = await findymail_client.generate_lead_list(
        query=body.query,
        target_job_titles=body.target_job_titles,
        mode=body.mode,
        find_contact=body.find_contact,
        find_email_flag=body.find_email,
        find_phone_flag=body.find_phone,
        limit=body.limit,
        api_key=settings.findymail_api_key,
        base_url=settings.findymail_base_url,
        timeout=settings.findymail_timeout,
    )
    return result


@router.post("/lead-results")
async def lead_results(body: GetLeadListResultsRequest, request: Request):
    err = _check_key()
    if err:
        return err
    result = await findymail_client.get_lead_list_results(
        hash_id=body.hash,
        api_key=settings.findymail_api_key,
        base_url=settings.findymail_base_url,
        timeout=settings.findymail_timeout,
    )
    return result
