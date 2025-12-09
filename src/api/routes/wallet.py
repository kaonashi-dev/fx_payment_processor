from fastapi import APIRouter, HTTPException, status, Depends
from src.services.wallet_service import WalletService
from src.api.dependencies import validate_user_exists
from src.schemas.wallet import (
    FundRequest,
    FundResponse,
    ConvertRequest,
    ConvertResponse,
    WithdrawRequest,
    WithdrawResponse,
    BalancesResponse,
    TransactionListResponse,
    TransactionResponse,
)

router = APIRouter(prefix="/wallets", tags=["Wallets API"])


@router.post(
    "/{user_id}/fund",
    response_model=FundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Fund a wallet",
    description="Add funds to a user's wallet in the specified currency. Creates the wallet if it doesn't exist.",
    responses={
        201: {
            "description": "Wallet successfully funded",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "user123",
                        "currency": "USD",
                        "amount": "100.00",
                        "new_balance": "100.00",
                        "message": "Wallet funded successfully",
                    }
                }
            },
        },
        400: {"description": "Invalid request (e.g., negative amount)"},
        404: {"description": "User not found"},
        422: {"description": "Validation error (e.g., unsupported currency)"},
        500: {"description": "Internal server error"},
    },
)
async def fund_wallet(
    request: FundRequest,
    user_id: str = Depends(validate_user_exists)
):
    try:
        result = WalletService.fund_wallet(
            user_id=user_id,
            currency=request.currency,
            amount=request.amount,
        )
        return FundResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error funding wallet: {str(e)}",
        )


@router.post(
    "/{user_id}/convert",
    response_model=ConvertResponse,
    status_code=status.HTTP_200_OK,
    summary="Convert currency",
    description="Convert funds between USD and MXN using current exchange rates. Requires sufficient balance in source currency.",
    responses={
        200: {
            "description": "Currency successfully converted",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "user123",
                        "from_currency": "USD",
                        "to_currency": "MXN",
                        "from_amount": "100.00",
                        "to_amount": "1870.00",
                        "fx_rate": "18.70",
                        "message": "Currency converted successfully",
                    }
                }
            },
        },
        400: {"description": "Insufficient balance or same currency conversion"},
        404: {"description": "User not found"},
        422: {"description": "Validation error (e.g., unsupported currency pair)"},
        500: {"description": "Internal server error"},
    },
)
async def convert_currency(
    request: ConvertRequest,
    user_id: str = Depends(validate_user_exists)
):
    try:
        result = WalletService.convert_currency(
            user_id=user_id,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
            amount=request.amount,
        )
        return ConvertResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error converting currency: {str(e)}",
        )


@router.post(
    "/{user_id}/withdraw",
    response_model=WithdrawResponse,
    status_code=status.HTTP_200_OK,
    summary="Withdraw funds",
    description="Withdraw funds from a user's wallet in the specified currency. Requires sufficient balance.",
    responses={
        200: {
            "description": "Funds successfully withdrawn",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "user123",
                        "currency": "USD",
                        "amount": "50.00",
                        "new_balance": "50.00",
                        "message": "Funds withdrawn successfully",
                    }
                }
            },
        },
        400: {"description": "Insufficient balance"},
        404: {"description": "User not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def withdraw_funds(
    request: WithdrawRequest,
    user_id: str = Depends(validate_user_exists)
):
    try:
        result = WalletService.withdraw_funds(
            user_id=user_id,
            currency=request.currency,
            amount=request.amount,
        )
        return WithdrawResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error withdrawing funds: {str(e)}",
        )


@router.get(
    "/{user_id}/balances",
    response_model=BalancesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get wallet balances",
    description="Retrieve all wallet balances for a user across all currencies.",
    responses={
        200: {
            "description": "Balances retrieved successfully",
            "content": {
                "application/json": {
                    "example": {"balances": {"USD": "500.00", "MXN": "9350.00"}}
                }
            },
        },
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_balances(
    user_id: str = Depends(validate_user_exists)
):
    try:
        balances = WalletService.get_balances(user_id)
        return BalancesResponse(balances=balances)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting balances: {str(e)}",
        )


@router.get(
    "/{user_id}/transactions",
    response_model=TransactionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get transaction history",
    description="Retrieve transaction history for a user, ordered by creation date (newest first). Limit specifies maximum number of transactions to return.",
    responses={
        200: {
            "description": "Transaction history retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "user123",
                        "transactions": [
                            {
                                "id": 3,
                                "user_id": "user123",
                                "transaction_type": "withdraw",
                                "currency": "USD",
                                "amount": "50.00",
                                "created_at": "2025-12-08T10:30:00",
                            },
                            {
                                "id": 2,
                                "user_id": "user123",
                                "transaction_type": "convert",
                                "from_currency": "USD",
                                "to_currency": "MXN",
                                "from_amount": "100.00",
                                "to_amount": "1870.00",
                                "fx_rate": "18.70",
                                "created_at": "2025-12-08T10:20:00",
                            },
                        ],
                        "total": 2,
                    }
                }
            },
        },
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_transactions(
    user_id: str = Depends(validate_user_exists),
    limit: int = 100
):
    try:
        transactions = WalletService.get_transactions(user_id, limit=limit)
        transaction_responses = [
            TransactionResponse(
                id=transaction.id,
                user_id=str(transaction.user_id),
                transaction_type=transaction.transaction_type,
                currency=transaction.currency,
                amount=transaction.amount,
                from_currency=transaction.from_currency,
                to_currency=transaction.to_currency,
                from_amount=transaction.from_amount,
                to_amount=transaction.to_amount,
                fx_rate=transaction.fx_rate,
                created_at=transaction.created_at,
            )
            for transaction in transactions
        ]
        return TransactionListResponse(
            user_id=user_id,
            transactions=transaction_responses,
            total=len(transaction_responses),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting transactions: {str(e)}",
        )
