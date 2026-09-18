/// All-time monthly averages from `GET /api/transactions/averages`.
class Averages {
  const Averages({required this.avgSpend, required this.avgSaving});

  /// Decimal amounts kept as strings for precision.
  final String avgSpend;
  final String avgSaving;

  factory Averages.fromJson(Map<String, dynamic> json) => Averages(
    avgSpend: json['avg_spend'].toString(),
    avgSaving: json['avg_saving'].toString(),
  );
}
