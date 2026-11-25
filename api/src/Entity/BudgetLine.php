<?php
namespace App\Entity;

use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'budget_lines')]
#[ORM\Index(name: 'idx_lines_budget', columns: ['budget_id'])]
#[ORM\Index(name: 'fk_line_category', columns: ['category_id'])]
class BudgetLine
{
    #[ORM\Id, ORM\Column(type: 'string', length: 36, options: ['fixed' => true])]
    public string $id;
    #[ORM\ManyToOne(targetEntity: MonthlyBudget::class), ORM\JoinColumn(name: 'budget_id', nullable: false, onDelete: 'CASCADE')]
    public MonthlyBudget $budget;
    #[ORM\ManyToOne(targetEntity: Category::class), ORM\JoinColumn(name: 'category_id', nullable: false, onDelete: 'RESTRICT')]
    public Category $category;
    #[ORM\Column(type: 'decimal', precision: 15, scale: 2)]
    public string $amount;
    #[ORM\Column(length: 255, options: ['default' => ''])]
    public string $notes = '';
}
